import uuid
import os
import logging
import json
import copy


from utils import helpers
from utils import http_helpers
import utils.cogvecsearch_helpers.cs_json
from utils import openai_helpers

from utils.env_vars import *
from utils import kb_doc
from utils import cv_helpers


class CogSearchVecStore:

    def __init__(self, api_key = COG_SEARCH_ADMIN_KEY, 
                       search_service_name = COG_SEARCH_ENDPOINT, 
                       index_name = COG_VECSEARCH_VECTOR_INDEX, 
                       api_version  = COG_VEC_SEARCH_API_VERSION,
                       load_addtl_fields = True):


        self.http_req = http_helpers.CogSearchHttpRequest(api_key, search_service_name, index_name, api_version)
        self.index_name = index_name
        self.all_fields = ['id', 'text', 'text_en', 'categoryId']
        self.search_types = ['vector', 'hybrid', 'semantic_hybrid']

        self.addtl_fields = []

        if load_addtl_fields:
            self.addtl_fields += list(kb_doc.KB_Doc().get_fields() - ['text', 'text_en', VECTOR_FIELD_IN_REDIS, 'id', 'cv_image_vector', 'cv_text_vector'])
            self.all_fields += self.addtl_fields



    def create_index(self):
        
        index_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.create_index_json)
        index_dict['name'] = self.index_name

        for f in self.addtl_fields:
            field_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.field_json)
            field_dict['name'] = f
            index_dict['fields'].append(field_dict)

        self.http_req.put(body = index_dict)


    def get_index(self):
        return self.http_req.get()


    def delete_index(self):
        return self.http_req.delete()


    def upload_documents(self, documents):

        docs_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.upload_docs_json)

        for doc in documents:
            doc_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.upload_doc_json)
                        
            for k in self.all_fields:
                doc_dict[k] = doc.get(k, '')

            doc_dict['id'] = doc['id'] if doc.get('id', None) else str(uuid.uuid4())
            doc_dict[VECTOR_FIELD_IN_REDIS] = doc.get(VECTOR_FIELD_IN_REDIS, [])
            doc_dict['cv_image_vector'] = doc.get('cv_image_vector', [])
            doc_dict['cv_text_vector'] = doc.get('cv_text_vector', [])
            doc_dict["@search.action"] = "upload"
            docs_dict['value'].append(doc_dict)
        
        self.http_req.post(op ='index', body = docs_dict)

        return docs_dict



    def delete_documents(self, op='index', ids = []):
        docs_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.upload_docs_json)

        for i in ids:
            doc_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.upload_doc_json)
            doc_dict['id'] = i
            doc_dict[VECTOR_FIELD_IN_REDIS] = [0] * openai_helpers.get_model_dims(CHOSEN_EMB_MODEL)
            doc_dict["@search.action"] = "delete"
            docs_dict['value'].append(doc_dict)

        self.http_req.post(op ='index', body = docs_dict)



    def search(self, query, search_type = 'vector', vector_name = None, select=None, filter=None, verbose=False):

        if search_type not in self.search_types:
            raise Exception(f"search_type must be one of {self.search_types}")

        if search_type == 'vector':
            query_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.search_dict_vector)
        elif search_type == 'hybrid':
            query_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.search_dict_hybrid)
            query_dict['search'] = query
        elif search_type == 'semantic_hybrid':
            query_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.search_dict_semantic_hybrid)
            query_dict['search'] = query

        
        query_dict = copy.deepcopy(utils.cogvecsearch_helpers.cs_json.search_dict_vector)
        

        if (vector_name is None) or (vector_name == VECTOR_FIELD_IN_REDIS):
            completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
            embedding_enc = openai_helpers.get_encoder(CHOSEN_EMB_MODEL)
            query_dict['vector']['fields'] = VECTOR_FIELD_IN_REDIS
            query = embedding_enc.decode(embedding_enc.encode(query)[:MAX_QUERY_TOKENS])
            query_dict['vector']['value'] = openai_helpers.get_openai_embedding(query, CHOSEN_EMB_MODEL)    
        elif vector_name in ['cv_text_vector', 'cv_image_vector']:
            cvr = cv_helpers.CV()
            query_dict['vector']['fields'] = vector_name
            query_dict['vector']['value'] = cvr.get_text_embedding(query)
        else:
            raise Exception(f'Invalid Vector Name {vector_name}')

        
        query_dict['vector']['k'] = NUM_TOP_MATCHES
        query_dict['filter'] = filter
        query_dict['select'] = ', '.join(self.all_fields) if select is None else select



        results = self.http_req.post(op ='search', body = query_dict)

        if verbose: [print(r['@search.score']) for r in results['value']]

        context = helpers.process_search_results(results['value'])

        return context





        
