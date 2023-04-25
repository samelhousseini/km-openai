
import uuid
import os
import logging
import json



from utils import http_helpers

COG_SEARCH_ENDPOINT = os.environ["COG_SEARCH_ENDPOINT"]
COG_SEARCH_ADMIN_KEY = os.environ["COG_SEARCH_ADMIN_KEY"]



class CogSearchVecSearch:
    def __init__(self, api_key = COG_SEARCH_ADMIN_KEY, search_service_name = COG_SEARCH_ENDPOINT, index_name = 'vec-index', api_version  = '2023-07-01-Preview'):
        self.http_req = http_helpers.HTTPRequest()
        self.http_req.initialize_for_cogsearch(api_key, search_service_name, index_name, api_version)