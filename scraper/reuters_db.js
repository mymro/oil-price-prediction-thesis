const db = require('better-sqlite3')('db.sqlite3');
const moment = require('moment');
const Queue = require('queue-fifo');

class db_helper{
    constructor(){
        this.update_tasks();
        this.task_done_helper = {};
    }

    update_tasks(){
        let task_arr = db.prepare("SELECT * FROM config WHERE done <> 1 AND site = 'reuters'").all();
        this.search_tasks = {};
        this.search_tasks_page_helper = {};
        for(let elem in task_arr){
            this.search_tasks[task_arr[elem].id] = task_arr[elem];
            this.search_tasks_page_helper[task_arr[elem].id] = {page: task_arr[elem].page, waiting:[]}
        }
    }

    hasSearchTasks(){
        return Object.keys(this.search_tasks).length > 0;
    }

    getSearchTask(){
        const id = Object.keys(this.search_tasks)[0];
        this.search_tasks[id].page += 1;
        const copy = {...this.search_tasks[id]}
        delete this.search_tasks[id];
        return copy;
    }

    setSearchTaskDone(id){
        //TODO add sophisticated logic to log a üage failing after complete was set
        db.prepare("UPDATE config SET done = 1 WHERE id = ?").run(id);
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
        db.prepare("INSERT INTO articles(url, title, date, search_term, site) VALUES(?, ?, ?, ?, 'reuters')").run(article.url, article.title, article.date, task.id);
    }

    articleDownloaded(article){
        db.prepare("UPDATE articles set filename = ?, fetched = 1 WHERE url = ?").run(article.filename, article.url);
    }
}

module.exports = new db_helper();