import sqlite3
import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from threading import Thread, Lock
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

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
article_cursor.execute("SELECT id, filename, sentiment_vader, sentiment_gnlp, magnitude_gnlp, site FROM articles WHERE sentiment_vader IS NULL OR sentiment_gnlp IS NULL AND fetched = 1")
update_cursor = conn.cursor()

db_lock = Lock()

def sentimenAnalysis():
    analyzer = SentimentIntensityAnalyzer()
    client = language.LanguageServiceClient()
    with db_lock:
        articles = article_cursor.fetchmany()

    while(len(articles) > 0):
        update_statements = []
        for article in articles:
            with open("../scraper/{0}_articles/{1}".format(article["site"], article["filename"]), "r", encoding="utf-8") as fl:
                logger.info("analyzing {0}".format(article["filename"]))
                vader = article["sentiment_vader"]
                gnlp = article["sentiment_gnlp"]
                gnlp_m = article["magnitude_gnlp"]
                text = fl.read()
                if(not vader):
                    vader = analyzer.polarity_scores(text)
                if(not gnlp):
                    document = {'type': enums.Document.Type.PLAIN_TEXT, 'content': text}
                    response = client.analyze_sentiment(document)
                    sentiment = response.document_sentiment
                    gnlp = sentiment.score
                    gnlp_m = sentiment.magnitude

                update_statements.append((vader, gnlp, gnlp_m, article["id"]))

        with db_lock:
            update_cursor.executemany("UPDATE articles set sentiment_vader=?, sentiment_gnlp=?, magnitude_gnlp=? WHERE id=?", update_statements)
            conn.commit()
            articles = article_cursor.fetchmany()


sentimenAnalysis()