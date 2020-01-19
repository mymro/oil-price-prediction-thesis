import sqlite3
import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from threading import Thread, Lock

logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)
f = logging.FileHandler("./log.txt")
f.setFormatter(formatter)
f.setLevel(logging.DEBUG)
logger.addHandler(f)

conn = sqlite3.connect('../scraper/db.sqlite3', check_same_thread=False)
conn.row_factory = sqlite3.Row
article_cursor = conn.cursor()
article_cursor.arraysize = 5
article_cursor.execute("SELECT id, filename, site FROM articles WHERE sentiment_score IS NULL AND fetched = 1")
update_cursor = conn.cursor()

db_lock = Lock()

logger.info("hi")

def sentimenAnalysis():
    analyzer = SentimentIntensityAnalyzer()
    with db_lock:
        articles = article_cursor.fetchmany()

    while(len(articles) > 0):
        update_statements = []
        for article in articles:
            with open("../scraper/{0}_articles/{1}".format(article["site"], article["filename"]), "r", encoding="utf-8") as fi:
                logger.info("analyzing {0}".format(article["filename"]))
                scores = analyzer.polarity_scores(fi.read())
                update_statements.append((scores["compound"], article["id"]))

        with db_lock:
            update_cursor.executemany("UPDATE articles set sentiment_score=? WHERE id=?", update_statements)
            conn.commit()
            articles = article_cursor.fetchmany()


sentimenAnalysis()