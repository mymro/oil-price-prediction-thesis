const cheerio = require('cheerio');
const puppeteer = require('puppeteer-extra');
const AdblockerPlugin = require('puppeteer-extra-plugin-adblocker');
const blockResourcesPlugin = require('puppeteer-extra-plugin-block-resources')({
    blockedTypes: new Set(['image', 'stylesheet', 'media', 'font'])
  })
const PromisePool = require('es6-promise-pool');
const genericPool = require("generic-pool");
const winston = require("winston");
const moment = require('moment-timezone');
const waitUntil = require('async-wait-until');
const fs = require('fs');
const { combine, timestamp, label, printf } = winston.format;
const db_helper = require('./cnbc_db');

const myFormat = printf(({ level, message}) => {
    return `${moment().format("YYYY-MM-DD HH:mm:ss.SSS")} ${level}: ${message}`;
  });

const logger = winston.createLogger({
    format: myFormat,
    transports: [
      new winston.transports.Console(),
      new winston.transports.File({ filename: 'cnbc.log'})
    ]
  });

const max_pages = 2;
const querly_data = {
    QuerylyKey: '',
    additionalindexes: '',
}

async function getQueryParameters(page_pool){
    let page = await page_pool.acquire();

    await page.goto("https://www.cnbc.com/search/?query=arabian%20oil&qsearchterm=arabian%20oil");
    await page.goto("https://fm.cnbc.com/applications/cnbc.com/resources/search/cnbc-queryly-search-R17.js");
    const js = await page.content();
    let start = js.indexOf("'", js.indexOf("QuerylyKey:")+10)
    let end = js.indexOf("'", start+1);
    if(start == -1 || end == -1){
        throw "QuerlyKey not found"
    }
    querly_data.QuerylyKey = js.slice(start+1, end);
    start = js.indexOf("'", js.indexOf("additionalindexes:", end)+17);
    end = js.indexOf("'", start +1);
    if(start == -1 || end == -1){
        throw "additionalindexes not found"
    }
    querly_data.additionalindexes = js.slice(start+1, end);
    page_pool.release(page);
    return page_pool;
}

async function getNewArticles(page_pool){
    const page = await page_pool.acquire();
    const task = db_helper.getSearchTask();
    logger.info(`Getting articles for ${task.search_term} on page ${task.page}`);
    await page.goto(`https://api.queryly.com/cnbc/json.aspx?queryly_key=${querly_data.QuerylyKey}&query=${task.search_term}&endindex=${(task.page-1)*10}&batchsize=${10}&callback=&showfaceted=true&timezoneoffset=0&facetedfields=formats&facetedkey=formats%7C&facetedvalue=Articles%7C&sort=date&additionalindexes=${querly_data.additionalindexes}`);
    const content = await page.content();
    let done = false;
    try{
        const json = await page.evaluate(() =>  {
            return JSON.parse(document.querySelector("body").innerText); 
        });
        if(json.results.length > 0){
            for(let elem in json.results){
                let article = {
                    title: json.results[elem]["cn:title"],
                    date: moment(json.results[elem]["datePublished"]).valueOf(),
                    url: json.results[elem]["cn:liveURL"]
                };
                if(article.date < task.min_date){
                    done = true;
                }
                logger.info(`Adding article: ${article.url}`)
                db_helper.addArticle(task, article);
            }
        }else{
            done = true;
        }
    }catch(error){
        done = true;
    }
    if(done){
        db_helper.setSearchTaskDone(task.id);
    }
    db_helper.pageDone(task);
    page_pool.release(page);
}

async function getArticle(page_pool){
    const page = await page_pool.acquire();
    const article = db_helper.getArticle();
    logger.info(`Loading article: ${article.url}`);
    await page.goto(article.url);
    const $ = cheerio.load(await page.content());
    article.filename = article.date+"_"+article.title.replace(/[\s\\\/\*:\?\"\<\>]+/g, "").substr(0, 10)+".txt";
    const file = fs.createWriteStream(`./cnbc_articles/${article.filename}`, { encoding: 'utf8' });
    $("div[class='ArticleBody-articleBody'] > div[class='group']").each(function(i, elem){
        $(this).find("p").each(function(i,elem){
            file.write($(this).text().replace(/\s+/g, " "));
        })
    });

    db_helper.articleDownloaded(article);
    page_pool.release(page);
}

let chrome = null;
logger.info("launching headless browser");
puppeteer.use(blockResourcesPlugin);
//puppeteer.use(AdblockerPlugin());
puppeteer.launch({
    headless: true,
    userDataDir: __dirname+"/chrome",
}).then(browser=>{
    chrome = browser;
    const factory = {
        create: function() {
            logger.debug("opening new page");
            async function gen(){
                let page = await chrome.newPage();
                page.setDefaultTimeout(120000);
                return(page);
            }
            return gen();
        },
        destroy: function(page) {
            return page.close().catch(console.log);
        }
    };
    return genericPool.createPool(factory, {min:1, max:max_pages});
}).then(page_pool=>{
    return getQueryParameters(page_pool);
}).then(page_pool=>{
    function promiseProducer(){
        if(db_helper.hasSearchTasks()){
            return getNewArticles(page_pool);
        }else if(db_helper.hasArticles()){
            return getArticle(page_pool);
        }else{
            return null;
        }
    }

    let promise_pool = new PromisePool(promiseProducer, max_pages);
    return promise_pool.start();
}).then(()=>{
    logger.info("done");
}).finally(()=>{
    chrome.close();
})