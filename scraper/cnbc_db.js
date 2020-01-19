const db = require('better-sqlite3')('db.sqlite3');
const moment = require('moment');
const Queue = require('queue-fifo');

class db_helper{
    constructor(){
        this.update_tasks();
        this.update_articles();
        this.task_done_helper = {};
    }

    update_tasks(){
        let task_arr = db.prepare("SELECT * FROM config WHERE done <> 1 AND site = 'cnbc'").all();
        this.search_tasks = {};
        this.search_tasks_page_helper = {};
        for(let elem in task_arr){
            this.search_tasks[task_arr[elem].id] = task_arr[elem];
            this.search_tasks_page_helper[task_arr[elem].id] = {page: task_arr[elem].page, waiting:[]}
        }
    }

    update_articles(){
        this.articles = new Queue;
        let articles_arr = db.prepare("SELECT articles.*, config.min_date AS min_date FROM articles LEFT JOIN config ON config.id = articles.search_term WHERE articles.fetched <> 1 AND articles.site = 'cnbc' ORDER BY articles.id ASC").all();
        for(let elem in articles_arr){
            this.articles.enqueue(articles_arr[elem]);
        }
    }

    hasArticles(){
        return this.articles.size() > 0;
    }

    getArticle(){
        return this.articles.dequeue();
    }

    articleDownloaded(article){
        db.prepare("UPDATE articles SET filename = ?, fetched = 1 WHERE url = ?")
            .run(article.filename, article.url);
    }

    hasSearchTasks(){
        return Object.keys(this.search_tasks).length > 0;
    }

    getSearchTask(){
        const id = Object.keys(this.search_tasks)[0];
        this.search_tasks[id].page += 1;
        return {...this.search_tasks[id]};
    }

    setSearchTaskDone(id){
        //TODO add sophisticated logic to log a üage failing after complete was set
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

    pageDone(task){
        if(this.search_tasks_page_helper[task.id].page + 1 === task.page){
            this.search_tasks_page_helper[task.id].page += 1;
            this.check_wating_pages(task);
            db.prepare("UPDATE config SET page = ? WHERE id = ?").run(this.search_tasks_page_helper[task.id].page, task.id);
        }else if(this.search_tasks_page_helper[task.id].page + 1 < task.page){
            this.search_tasks_page_helper[task.id].waiting.push(task.page);
        }
    }

    addArticle(task, article){
        try {
            db.prepare("INSERT INTO articles(url, title, date, search_term, site) VALUES(?, ?, ?, ?, 'cnbc')").run(article.url, article.title, article.date, task.id);
            this.articles.enqueue({url:article.url, title:article.title, date:article.date, search_term: task.id, min_date: task.min_date});
        } catch (error) {
            console.log("article already exists");
        }
    }
}

module.exports = new db_helper();