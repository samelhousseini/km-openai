
import os
import json

KB_INDEX_NAME = os.environ.get("KB_INDEX_NAME")

class KB_Doc():

    def __init__(self):

        self.id = ''
        self.text_en = ''
        self.text = ''
        self.doc_url = ''
        self.timestamp = ''
        self.item_vector = []
        self.orig_lang = 'en'
        self.access = 'public'
        self.client = KB_INDEX_NAME


    def load(self, data):
        for k in data:
            setattr(self, k, data[k])


    def get_dict(self):
        return {
                    'id': self.id,
                    'text_en': self.text_en, 
                    'text': self.text, 
                    'doc_url':  self.doc_url, 
                    'timestamp': self.timestamp, 
                    'item_vector': self.item_vector,
                    'orig_lang': self.orig_lang,
                    'access': self.access,
                    'client': self.client
                }