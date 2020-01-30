const db = require('better-sqlite3')('db.sqlite3');
const moment = require('moment');
const Queue = require('queue-fifo');

class db_helper{
    constructor(){
        this.update_tasks();
        this.update_articles();
    }

    update_tasks(){
        let task_arr = db.prepare("SELECT * FROM config WHERE done <> 1 AND site = 'upi'").all();
        this.search_tasks = {};
        this.search_tasks_page_helper = {};
        for(let elem in task_arr){
            this.search_tasks[task_arr[elem].id] = task_arr[elem];
            this.search_tasks_page_helper[task_arr[elem].id] = {page: task_arr[elem].page, waiting:[]}
        }
    }

    update_articles(){
        this.articles = new Queue;
        let articles_arr = db.prepare("SELECT articles.*, config.min_date AS min_date FROM articles LEFT JOIN config ON config.id = articles.search_term WHERE articles.fetched <> 1 AND articles.site = 'upi' ORDER BY articles.id ASC").all();
        for(let elem in articles_arr){
            this.articles.enqueue(articles_arr[elem]);
        }
    }

    waiting_articles(){
        return this.articles.size();
    }

    get_article(){
        return this.articles.dequeue();
    }

    article_downloaded(article){
        db.prepare("UPDATE articles SET title = ?, date = ?, filename = ?, fetched = 1 WHERE url = ?")
            .run(article.title, article.date, article.filename, article.url);
    }

    has_search_tasks(){
        return Object.keys(this.search_tasks).length > 0;
    }

    get_search_task(){
        const id = Object.keys(this.search_tasks)[0];
        this.search_tasks[id].page += 1;
        return {...this.search_tasks[id]};
    }

    set_search_task_done(id){
        db.prepare("UPDATE config SET done = 1 WHERE id = ?").run(id);
        delete this.search_tasks[id];
    }

    check_wating_pages(task){
        if(this.search_tasks_page_helper[task.id].waiting.length > 0){
            this.search_tasks_page_helper[task.id].waiting.sort(function(a, b){return a-b});
            while(this.search_tasks_page_helper[task.id].page+1 === this.search_tasks_page_helper[task.id].waiting[0]){
                this.search_tasks_page_helper[task.id].page += 1;
                this.search_tasks_page_helper[task.id].waiting.shift();
            }
        }
    }

    page_done(task){
        if(this.search_tasks_page_helper[task.id].page + 1 === task.page){
            this.search_tasks_page_helper[task.id].page += 1;
            this.check_wating_pages(task);
            db.prepare("UPDATE config SET page = ? WHERE id = ?").run(this.search_tasks_page_helper[task.id].page, task.id);
        }else if(this.search_tasks_page_helper[task.id].page + 1 < task.page){
            his.search_tasks_page_helper[task.id].waiting.push(task.page);
        }
    }

    add_article(task, url){
        try {
            db.prepare("INSERT INTO articles(url, search_term, site) VALUES(?, ?, 'upi')").run(url, task.id);
            this.articles.enqueue({url:url, search_term: task.id, min_date: task.min_date});
        } catch (error) {
            console.log(error);
        }
    }
}

module.exports = new db_helper();