import re
from os import walk
import sqlite3
from threading import Thread, Lock

conn = sqlite3.connect('../scraper/db.sqlite3', check_same_thread=False)
conn.row_factory = sqlite3.Row
article_cursor = conn.cursor()
article_cursor.arraysize = 5
article_cursor.execute("SELECT * FROM articles where cleaned <> 1")
update_cursor = conn.cursor()

db_lock = Lock()


def clean():
        
    with db_lock:
        articles = article_cursor.fetchmany()

    while len(articles) > 0:
        ids = []
        for article in articles:
            with open("../scraper/{0}_articles/{1}".format(article["site"], article["filename"]), "r+", encoding="utf-8") as f:
                text = re.sub(r"\s+", " ", f.read()).strip()
                f.seek(0)
                f.truncate()
                f.write(text)
                ids.append(article["id"])
        
        with db_lock:
            update_cursor.execute(f"UPDATE articles SET cleaned = 1 WHERE id IN({','.join(['?']*len(ids))})", ids)
            conn.commit()
            articles = article_cursor.fetchmany()


threads = []
for i in range(16):
    process = Thread(target=clean)
    threads.append(process)

[t.start() for t in threads]
[t.join() for t in threads]

conn.close()
