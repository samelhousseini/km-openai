import uuid
import os
import logging
import json
import copy


from utils import http_helpers
from utils import openai_helpers

from utils.env_vars import *




class CV:

    def __init__(self, api_key = COG_SERV_KEY, 
                       cog_serv_name = COG_SERV_ENDPOINT, 
                       api_version  = CV_API_VERSION):


        self.http_req = http_helpers.CVHttpRequest(api_key, cog_serv_name, api_version)



    def process_json(self, img_url, response):
        res = {}

        res['main_caption'] = response['captionResult']['text']
        res['tags'] = [tag['name'] for tag in response['tagsResult']['values']]
        res['ocr'] = response['readResult']['content']
        res['captions'] = [caption['text'] for caption in response['denseCaptionsResult']['values']]

        res['text'] = f"[{img_url}] This is an image. Main Caption: {res['main_caption']}\nOCR: {res['ocr']}\nDense Captions: {', '.join(res['captions'])}\nTags: {', '.join(res['tags'])}"

        return res



    def analyze_image(self, img_url = None, filename = None):

        if filename is not None: 
        
            with open(filename, 'rb') as f:
                data = f.read()
            response = self.http_req.post(op='analyze', data=data)

        else:
            response = self.http_req.post(op='analyze', headers=self.http_req.json_headers, body={'url': img_url})
            
        response = self.process_json(img_url, response)

        return response


    def get_img_embedding(self, img_url = None, filename = None):

        if filename is not None: 
            with open(filename, 'rb') as f:
                data = f.read()
            
            response = self.http_req.post(op='img_embedding', data=data)
        else:

            response = self.http_req.post(op='img_embedding', headers=self.http_req.json_headers, body={'url': img_url})

        try:
            return response['vector']
        except:
            return None



    def get_text_embedding(self, text):
        response = self.http_req.post(op='text_embedding', headers=self.http_req.json_headers, body={'text': text})

        try:
            return response['vector']
        except:
            return None