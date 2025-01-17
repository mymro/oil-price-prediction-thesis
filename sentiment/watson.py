
import json
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, SentimentOptions
# from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

with open("ibm-credentials.txt") as f:
    watson_key = f.read()

authenticator = IAMAuthenticator(watson_key)
service = NaturalLanguageUnderstandingV1(
    version='2018-03-16',
    authenticator=authenticator)
service.set_service_url('https://gateway.watsonplatform.net/natural-language-understanding/api')

# Authentication via external config like VCAP_SERVICES

#service = NaturalLanguageUnderstandingV1(
    #version='2018-03-16')
#service.set_service_url('https://gateway.watsonplatform.net/natural-language-understanding/api')

response = service.analyze(
    text='Bruce Banner is the Hulk and Bruce Wayne is BATMAN! '
    'Superman fears not Banner, but Wayne.',
    features=Features(sentiment=SentimentOptions())).get_result()

print(response["sentiment"]["document"]["score"])