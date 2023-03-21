import os
import pickle
import numpy as np
import logging

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

from utils import storage

COG_SERV_ENDPOINT = os.environ['COG_SERV_ENDPOINT']
COG_SERV_KEY = os.environ['COG_SERV_KEY']
FR_CONTAINER = os.environ['FR_CONTAINER']
OUTPUT_BLOB_CONTAINER = os.environ['OUTPUT_BLOB_CONTAINER']


document_analysis_client = DocumentAnalysisClient(COG_SERV_ENDPOINT, AzureKeyCredential(COG_SERV_KEY))



def process_forms(in_container = FR_CONTAINER, out_container = OUTPUT_BLOB_CONTAINER): 
    blob_list = storage.list_documents(in_container)

    for b in blob_list:
        url = storage.create_sas(b)
        result = fr_analyze_doc(url)

        new_json = {
            'text': result,
            'doc_url': b
        }

        storage.save_json_document(new_json, container = out_container )





def fr_analyze_doc(url):

    poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-document", url)
    result = poller.result()

    contents = ''

    for paragraph in result.paragraphs:
        contents += paragraph.content + '\n'

    for kv_pair in result.key_value_pairs:
        key = kv_pair.key.content if kv_pair.key else ''
        value = kv_pair.value.content if kv_pair.value else ''
        kv_pairs_str = f"{key} : {value}"
        contents += kv_pairs_str + '\n'

    for table_idx, table in enumerate(result.tables):
        row = 0
        row_str = ''
        row_str_arr = []

        for cell in table.cells:
            if cell.row_index == row:
                row_str += ' | ' + str(cell.content)
            else:
                row_str_arr.append(row_str)
                row_str = ''
                row = cell.row_index
                row_str += ' | ' + str(cell.content)

        row_str_arr.append(row_str)
        contents += '\n'.join(row_str_arr) +'\n'

    return contents