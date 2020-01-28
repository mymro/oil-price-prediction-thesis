const db = require('better-sqlite3')('db.sqlite3');
const fs = require('fs')

let articles = db.prepare("SELECT * FROM articles WHERE site = 'reuters' AND filename IS NULL").all();

for(let ele in articles){
    let article = articles[ele];
    article.filename = article.date+"_"+article.title.replace(/[\s\\\/\*:\?\"\<\>]+/g, "").substr(0, 10)+".txt";
    try{
        if(ele%200 == 0){
            console.log(ele);
        }
        if(fs.existsSync("./reuters_articles/"+article.filename)){
            db.prepare("UPDATE articles set filename = ?, fetched = 1 WHERE url = ?").run(article.filename, article.url);
        }else{
            console.log("no file for "+article.title);
        }
    }catch(error){
        console.log(error);
        console.log(article.filename);
    }
}