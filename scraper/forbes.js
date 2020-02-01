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
const db_helper = require('./forbes_db');

const myFormat = printf(({ level, message}) => {
    return `${moment().format("YYYY-MM-DD HH:mm:ss.SSS")} ${level}: ${message}`;
  });

const logger = winston.createLogger({
    format: myFormat,
    transports: [
      new winston.transports.Console(),
      new winston.transports.File({ filename: 'forbes.log'})
    ]
  });

const max_pages = 2;
let running_searches = 0;

async function getCookies(page_pool){
    let page = await page_pool.acquire();

    await page.goto("https://www.forbes.com/search/?q=oil#64a0092b279f");
    await page.content();
    page_pool.release(page);
    return page_pool;
}

async function getNewArticles(page_pool){
    running_searches += 1;
    const task = db_helper.getSearchTask();
    const page = await page_pool.acquire();
    logger.info(`Getting articles for ${task.search_term} on page ${task.page}`);
    await page.goto(`https://www.forbes.com/simple-data/search/more/?start=${(task.page-1)*20}&sort=recent&q=%22${task.search_term}%22`);
    const content = await page.content();
    let done = false;

    const $ = cheerio.load(content);
    $("article").each(function(i,elem){
        let article = {};
        title = $(this).find("div[class='stream-item__text'] > h2");
        article.title = title.text();
        article.url = title.find("a").attr("href");
        article.date = parseInt($(this).find("div[class='stream-item__text'] > div[class='stream-item__date']").attr("data-date"));
        try{
            db_helper.addArticle(task, article);
        }catch(error){
            logger.error(error);
        }
        if(article.date < task.min_date){
            done = true;
        }
    })

    if(done){
        db_helper.setSearchTaskDone(task.id);
    }
    db_helper.pageDone(task);
    page_pool.release(page);
    running_searches -= 1;
}

async function getArticle(page_pool){
    const article = db_helper.getArticle();
    const page = await page_pool.acquire();
    logger.info(`Loading article: ${article.url}`);
    try{
        await page.goto(article.url);
        const $ = cheerio.load(await page.content());
        article.filename = article.date+"_"+article.title.replace(/[\s\\\/\*:\?\"\<\>]+/g, "").substr(0, 20)+".txt";
        const file = fs.createWriteStream(`./forbes_articles/${article.filename}`, { encoding: 'utf8' });
        $("article-body-container > div > div > p").each(function(i, elem){
            file.write(($(this).text().replace(/\s+/g, " "))+" ");
        });
    
        db_helper.articleDownloaded(article);
    }catch(error){
        logger.error(error);
        db_helper.articleFailed(article);
    }
    page_pool.release(page);
}

function generateWaitCondition(running_queries){
    return(()=>{
        return running_searches < running_queries
    })
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
    return getCookies(page_pool);
}).then(page_pool=>{
    function promiseProducer(){
        if(db_helper.hasSearchTasks()){
            return getNewArticles(page_pool);   
        }else if(db_helper.hasArticles()){
            return getArticle(page_pool);
        }else if(running_searches > 0){
            logger.info("waiting for articles")
            return waitUntil(generateWaitCondition(running_searches), 140000).catch(()=>{
                logger.error("article query did not finish in time")
            });
        }else{
            return null;
        }
    }

    let promise_pool = new PromisePool(promiseProducer, max_pages);
    return promise_pool.start();
}).then(()=>{
    logger.info("done");
}).catch(error=>{
    logger.error(error);
}).finally(()=>{
    chrome.close();
})