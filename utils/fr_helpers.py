import os
import pickle
import numpy as np
import logging
import pandas as pd
import numpy as np

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
            'doc_url': b,
            'container': in_container,
            'filename': storage.get_filename(b),
            'web_url': ''
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


def fr_analyze_local_doc_with_dfs(path, verbose = True):

    with open(path, "rb") as f:
        poller = document_analysis_client.begin_analyze_document("prebuilt-document", document=f)

    result = poller.result()
    
    contents = ''
    kv_contents = ''
    t_contents = ''

    for kv_pair in result.key_value_pairs:
        key = kv_pair.key.content if kv_pair.key else ''
        value = kv_pair.value.content if kv_pair.value else ''
        kv_pairs_str = f"{key} : {value}"
        kv_contents += kv_pairs_str + '\n'

    for paragraph in result.paragraphs:
        contents += paragraph.content + '\n'


    for table_idx, table in enumerate(result.tables):
        row = 0
        row_str = ''
        row_str_arr = []

        for cell in table.cells:
            if cell.row_index == row:
                row_str += ' \t ' + str(cell.content)
            else:
                row_str_arr.append(row_str )
                row_str = ''
                row = cell.row_index
                row_str += ' \t ' + str(cell.content)

        row_str_arr.append(row_str )
        t_contents += '\n'.join(row_str_arr) +'\n\n'  
            
    dfs = []

    # for idx, table in enumerate(result.tables):
        
    #     field_list = [c['content'] for c in table.to_dict()['cells'] if c['kind'] == 'columnHeader'] 
    #     print('\n', field_list)
        
    #     table_dict = table.to_dict()
    #     row_count = table_dict['row_count']
    #     col_count = table_dict['column_count']

    #     cells = [c for c in table_dict['cells'] if c['kind'] == 'content']
    #     rows = []
    #     max_cols = 0

    #     for i in range(row_count - 1):
    #         row = [c['content'] for c in cells if c['row_index'] == i + 1]
    #         # print(row, i)
    #         if len(row) > 0: rows.append(row)
    #         if len(row) > max_cols: max_cols = len(row)

    #     if len(field_list) < max_cols: field_list += [''] * (max_cols - len(field_list))
    #     df = pd.DataFrame(rows, columns=field_list)
    #     if verbose: display(df)
    #     dfs.append(df)

      

    return contents, kv_contents, dfs, t_contents