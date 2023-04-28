import os
import json
from datetime import datetime, timedelta

from utils.env_vars import *

class KB_Doc():

    def __init__(self):

        self.id = ''
        self.text_en = ''
        self.text = ''
        self.doc_url = ''
        self.timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        self.item_vector = []
        self.orig_lang = 'en'
        self.access = 'public'
        self.client = KB_INDEX_NAME
        self.container = KB_BLOB_CONTAINER
        self.filename = ''
        self.web_url = ''


    def load(self, data):
        for k in data:
            setattr(self, k, data[k])


    def get_fields(self):
        return self.__dict__.keys()


    def get_dict(self):
        return self.__dict__