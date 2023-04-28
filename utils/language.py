
import requests
import uuid
import os
import logging

import typing
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient

from utils.env_vars import *

def detect_content_language(content):
    path = '/detect'
    constructed_url = TRANSLATION_ENDPOINT + path

    params = {
        'api-version': '3.0',
    }

    headers = {
        'Ocp-Apim-Subscription-Key': TRANSLATION_API_KEY,
        'Ocp-Apim-Subscription-Region': TRANSLATION_LOCATION,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    # You can pass more than one object in body.
    body = [{'text': content}]

    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()

    try:
        lang = response[0]['language']
        return lang
    except: 
        return 'xx'




def translate(text, from_lang, to_lang = 'en'):

    path = '/translate'
    constructed_url = TRANSLATION_ENDPOINT + path
    body = [{'text': text}]

    params = {
        'api-version': '3.0',
        'from': from_lang,
        'to': [to_lang]
    }

    headers = {
        'Ocp-Apim-Subscription-Key': TRANSLATION_API_KEY,
        'Ocp-Apim-Subscription-Region': TRANSLATION_LOCATION,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()

    try:
        # print(response)
        return response[0]['translations'][0]['text']
    except Exception as e:
        print(e)
        return response



def extract_entities(text):

    text_analytics_client = TextAnalyticsClient(endpoint=COG_SERV_ENDPOINT, credential=AzureKeyCredential(COG_SERV_KEY))
    reviews = [text]

    result = text_analytics_client.recognize_entities(reviews)
    result = [review for review in result if not review.is_error]
    organization_to_reviews: typing.Dict[str, typing.List[str]] = {}

    entities = []

    for idx, review in enumerate(result):
        for entity in review.entities:
            entities.append(entity.text)
            #print(entity.text)
    
    return entities