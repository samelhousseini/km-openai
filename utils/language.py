
import requests
import uuid
import os
import logging

TRANSLATION_API_KEY = os.environ["TRANSLATION_API_KEY"]
TRANSLATION_ENDPOINT = os.environ["TRANSLATION_ENDPOINT"]
TRANSLATION_LOCATION = os.environ["TRANSLATION_LOCATION"]



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

    return response[0]['translations'][0]['text']