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
const db_helper = require('./reuters_db');

const myFormat = printf(({ level, message}) => {
    return `${moment().format("YYYY-MM-DD HH:mm:ss.SSS")} ${level}: ${message}`;
  });

const logger = winston.createLogger({
    format: myFormat,
    transports: [
      new winston.transports.Console(),
      new winston.transports.File({ filename: 'reuters.log'})
    ]
  });

const max_pages = 3;

async function getNewArticles(page_pool){
    const page = await page_pool.acquire();
    const task = db_helper.getSearchTask();
    logger.info(`Getting articles for ${task.search_term} on page ${task.page}`);
    const url = `https://www.reuters.com/search/news?sortBy=date&dateRange=all&blob=${task.search_term}`;
    await page.goto(url);

    let done = false;
    while(!done){
        try{
            let json = await page.evaluate(async (task) => {
                const response = await fetch(`https://www.reuters.com/assets/searchArticleLoadMoreJson?blob=${task.search_term}&bigOrSmall=big&articleWithBlog=true&sortBy=date&dateRange=all&numResultsToShow=10&pn=${task.page}&callback=addMoreNewsResults`);
                let string = await response.text();
                string = string.substring(string.indexOf("( {")+2, string.lastIndexOf("]}")+2)
                return string;
              }, task);
            json = eval("("+json+")");
            if(json.news.length > 0){
                for(let elem in json.news){
                    let article = {
                        title: cheerio.load(json.news[elem]["headline"]).text(),
                        date: moment.tz(json.news[elem]["date"], "MMMM DD, YYYY hh:mma", "Etc/GMT+5").valueOf(),
                        url: "https://www.reuters.com"+json.news[elem]["href"]
                    };
                    if(article.date < task.min_date){
                        done = true;
                    }
                    logger.info(`Adding article for ${task.search_term}: ${article.url}`)
                    await getArticle(article, page, task);
                }
            }else{
                done = true;
            }
        }catch(error){
            logger.error(error);
            logger.error(`task faild for ${task.search_term}`);
			page_pool.release(page);
            return;
        }
        db_helper.pageDone(task);
        task.page += 1;
    }

    db_helper.setSearchTaskDone(task.id);
    page_pool.release(page);
}

async function getArticle(article, page, task){
    await page.goto(article.url);
    article.url = page.url();
    try{
        db_helper.addArticle(task, article);
    }catch(error){
        logger.info(`article: ${article.url} does already exist`);
        return;
    }
    const $ = cheerio.load(await page.content());
	const rand = Math.floor(Math.random() * 100);
    article.filename = article.date+"_"+article.title.replace(/[\s\\\/\*:\?\"\<\>]+/g, "").substr(0, 20)+rand+".txt";
    const file = fs.createWriteStream(`./reuters_articles/${article.filename}`, { encoding: 'utf8' });
    $("div[class='StandardArticleBody_container'] > div[class='StandardArticleBody_body']>p").each(function(i, elem){
        file.write($(this).text().replace(/\s+/g, ""));
    });

    logger.info(`downloaded ${article.url}`);
    db_helper.articleDownloaded(article);
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
    function promiseProducer(){
        if(db_helper.hasSearchTasks()){
            return getNewArticles(page_pool);
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