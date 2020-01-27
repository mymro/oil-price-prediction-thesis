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
const db_helper = require('./upi_db');

const myFormat = printf(({ level, message}) => {
    return `${moment().format("YYYY-MM-DD HH:mm:ss.SSS")} ${level}: ${message}`;
  });

const logger = winston.createLogger({
    format: myFormat,
    transports: [
      new winston.transports.Console(),
      new winston.transports.File({ filename: 'upi.log'})
    ]
  });

const max_pages = 2;
let running_article_queries = 0;

function generateWaitCondition(running_queries){
    return(()=>{
        return running_article_queries < running_queries
    })
}

async function getNewArticles(page_pool){
    running_article_queries += 1;
    const my_task = db_helper.get_search_task();

    const page = await page_pool.acquire();
    logger.info(`Getting articles for ${my_task.search_term} page:${my_task.page}`);
    await page.goto(`https://www.upi.com/search/?s_l=articles&ss=${my_task.search_term}&s_term=ea&offset=${my_task.page}`);
    const $ = cheerio.load(await page.content());
    let nodes = $("div[class='row story list'] > .col-md-12")
    if(nodes.length === 0){
        logger.info(`Articles for ${my_task.search_term} ended on page ${my_task.page}. Jumping to next search term`)
        db_helper.set_search_task_done(my_task.id);
    }else{
        nodes.each(function(i, elem){
            let link = $(this).find('a').attr('href');
            let url = link.slice(0, link.lastIndexOf("/"));
            logger.debug(`found: ${url}`);

            db_helper.add_article(my_task, url);
        })
    }
    db_helper.page_done(my_task, page)
    page_pool.release(page);
    running_article_queries -= 1;
}

async function fetchNextArticle(page_pool){
    const article = db_helper.get_article();
    const page = await page_pool.acquire();
    logger.info(`Fetching article from: ${article.url}`);
    let $;
    try{
        await page.goto(article.url);
        $ = cheerio.load(await page.content());
    }catch(error){
        logger.error(`failed to fetch: ${article.url}`);
        return;
    }
    article.title = $("div.news-head > h1.headline").text();
    article.date = moment.tz($("div.news-head > div.montserrat > div.article-date").text().trim(), "MMM. D, YYYY / h:m a", "Etc/GMT+5").valueOf();
    article.filename = article.date+"_"+article.title.replace(/[\s\\\/\*:\?\"\<\>]+/g, "").substr(0, 10)+".txt";
    const file = fs.createWriteStream(`./upi_articles/${article.filename}`, { encoding: 'utf8' });
    $("article[itemprop='articleBody'] > p").each(function(i, elem){
        file.write($(this).text().replace(/[\r\n]+/g, ""));
    });
    if(article.date < article.min_date){
        db_helper.set_search_task_done(article.search_term);
    }
    db_helper.article_downloaded(article);
    page_pool.release(page);
}

let chrome = null;

logger.info("launching headless browser");
puppeteer.use(blockResourcesPlugin);
//puppeteer.use(AdblockerPlugin());
puppeteer.launch({
    headless:true,
    userDataDir: __dirname+"/chrome"
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
            return page.close();
        }
    };
    return genericPool.createPool(factory, {min:1, max:max_pages});

}).then(page_pool=>{
    function promiseProducer(){
        if(db_helper.waiting_articles() < 5
            && db_helper.has_search_tasks()
            && running_article_queries < 1){

            return getNewArticles(page_pool);
        }else if(db_helper.waiting_articles() == 0 
            && running_article_queries > 0){
            
            logger.info("waiting for new articles");
            return waitUntil(generateWaitCondition(running_article_queries), 120000).catch();
        }else if(db_helper.waiting_articles() > 0){

            return fetchNextArticle(page_pool);
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