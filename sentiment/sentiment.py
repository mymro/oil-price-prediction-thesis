import sqlite3
import logging
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from threading import Thread, Lock
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, SentimentOptions
from nltk import tokenize

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)
f = logging.FileHandler("./log.txt")
f.setFormatter(formatter)
f.setLevel(logging.INFO)
logger.addHandler(f)

conn = sqlite3.connect('../scraper/db.sqlite3', check_same_thread=False)
conn.row_factory = sqlite3.Row
article_cursor = conn.cursor()
article_cursor.arraysize = 5
article_cursor.execute("SELECT id, filename, sentiment_vader, sentiment_vader_average, sentiment_gnlp, magnitude_gnlp, sentiment_watson, site FROM articles WHERE sentiment_vader IS NULL OR sentiment_vader_average IS NULL OR sentiment_watson IS NULL AND fetched = 1")
update_cursor = conn.cursor()

db_lock = Lock()
with open("ibm-credentials.txt") as f:
    watson_key = f.read()

def sentimenAnalysis():
    analyzer = SentimentIntensityAnalyzer()
    client = language.LanguageServiceClient()

    authenticator = IAMAuthenticator(watson_key)
    service = NaturalLanguageUnderstandingV1(
        version='2018-03-16',
        authenticator=authenticator)
    service.set_service_url('https://gateway.watsonplatform.net/natural-language-understanding/api')

    with db_lock:
        articles = article_cursor.fetchmany()

    while(len(articles) > 0):
        update_statements = []
        for article in articles:
            with open("../scraper/{0}_articles/{1}".format(article["site"], article["filename"]), "r", encoding="utf-8") as fl:
                vader = article["sentiment_vader"]
                vader_average = article["sentiment_vader_average"]
                gnlp = article["sentiment_gnlp"]
                gnlp_m = article["magnitude_gnlp"]
                watson = article["sentiment_watson"]
                text = fl.read()
                if(len(text)>0):
                    try:
                        if(not vader):
                            logger.info("getting vader for {0}".format(article["filename"]))
                            vader = analyzer.polarity_scores(text)["compound"]
                        if(not vader_average):
                            logger.info("getting vader compound for {0}".format(article["filename"]))
                            lines_list = tokenize.sent_tokenize(text)
                            compound = 0
                            for line in lines_list:
                                compound += analyzer.polarity_scores(line)["compound"]
                            vader_average = compound/len(lines_list)
                        #if(not gnlp):
                            #logger.info("getting google nlp for {0}".format(article["filename"]))
                            #document = {'type': enums.Document.Type.PLAIN_TEXT, 'content': text}
                            #response = client.analyze_sentiment(document)
                            #sentiment = response.document_sentiment
                            #gnlp = sentiment.score
                            #gnlp_m = sentiment.magnitude
                        if(not watson):
                            logger.info("getting watson sentiment for {0}".format(article["filename"]))
                            response = service.analyze(
                                text=text,
                                features=Features(sentiment=SentimentOptions())
                            ).get_result()
                            watson = response["sentiment"]["document"]["score"]
                    except Exception as e:
                        logger.error("error for: " + article["filename"])
                        logger.error(e)
						
                update_statements.append((vader, vader_average, gnlp, gnlp_m, watson, article["id"]))

        with db_lock:
            update_cursor.executemany("UPDATE articles set sentiment_vader=?, sentiment_vader_average=?, sentiment_gnlp=?, magnitude_gnlp=?, sentiment_watson=? WHERE id=?", update_statements)
            conn.commit()
            articles = article_cursor.fetchmany()

threads = []
for i in range(8):
    process = Thread(target=sentimenAnalysis)
    threads.append(process)

[t.start() for t in threads]
[t.join() for t in threads]

conn.close()