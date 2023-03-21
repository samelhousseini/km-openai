import logging
import json
import re
import azure.functions as func
import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import ContainerClient
import urllib
import uuid

from utils import cosmos_helpers
from utils import storage


DATABASE_MODE = os.environ['DATABASE_MODE']
COSMOS_URI  = os.environ['COSMOS_URI']
COSMOS_KEY  = os.environ['COSMOS_KEY']
COSMOS_DB_NAME   = os.environ['COSMOS_DB_NAME']
CATEGORYID  = os.environ['CATEGORYID']

KB_BLOB_CONTAINER = os.environ['KB_BLOB_CONTAINER'] 
KB_BLOB_CONN_STR = os.environ['KB_BLOB_CONN_STR']
OUTPUT_BLOB_CONTAINER = os.environ['OUTPUT_BLOB_CONTAINER']


def remove_urls(text):
    text = re.sub(r'(https|http)?:\/\/(\w|\.|\/|\?|\=|\&|\%)*\b', '', text, flags=re.MULTILINE)
    return text

re_strs = [
    "customXml\/[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*", 
    "ppt\/[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*",
    "\.MsftOfcThm_[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*[\r\n\t\f\v ]\{[\r\n\t\f\v ].*[\r\n\t\f\v ]\}",
    "SlidePowerPoint",
    "PresentationPowerPoint",
    '[a-zA-Z0-9]*\.(?:gif|emf)'
    ]



def analyze_doc(data_dict):
    
    ret_dict = {}
    db_status = ''
    data_dict['text'] = remove_urls(data_dict['content'].replace("\n\n", " ").replace("....", " ")).replace("\n\n", " ").replace("\n", " ")

    data_dict['container'] = storage.get_container_name(data_dict['doc_url'])

    for re_str in re_strs:
        matches = re.findall(re_str, data_dict['text'], re.DOTALL)
        for m in matches: data_dict['text'] = data_dict['text'].replace(m, '')

    try:
        if DATABASE_MODE == '1':
            db_status = cosmos_helpers.cosmos_store_contents(data_dict)
            logging.info(db_status)
            print(db_status)
    except Exception as e:    
        doc_id = data_dict.get('id', 'Unknown ID')
        logging.error(f"Exception: Document {doc_id} created an exception.\n{e}")
        ret_dict['status'] = f"Exception: Document {doc_id} created an exception.\n{e}"

    try:
        ret_dict = storage.save_json_document(data_dict, OUTPUT_BLOB_CONTAINER)
        logging.info(ret_dict['status'])
    except Exception as e:
        doc_id = data_dict.get('id', 'Unknown ID')
        logging.error(f"Exception: Document {doc_id} created an exception.\n{e}")
        ret_dict['status'] = f"Exception: Document {doc_id} created an exception.\n{e}"

    return ret_dict




## Perform an operation on a record
def transform_value(value):
    try:
        recordId = value['recordId']
    except AssertionError  as error:
        logging.info(error)
        return None

    # Validate the inputs
    try:         
        assert ('data' in value), "'data' field is required."
        data = value['data']        
        logging.info(f"Data received: {data}")
        assert ('content' in data), "'content' field is required in 'data' object."
        assert ('id' in data), "'id' field is required in 'data' object."
        
    except AssertionError as error:
        logging.info(error)
        return (
            {
            "recordId": recordId,
            "errors": [ { "message": "Error:" + error.args[0] }   ]       
            })

    try:                
        ret_dict = analyze_doc(value['data'])
                               
        # Here you could do something more interesting with the inputs

    except AssertionError  as error:
        logging.info(error)
        return (
            {
            "recordId": recordId,
            "errors": [ { "message": "Could not complete operation for record." }   ]       
            })

    return ({
            "recordId": recordId,
            "data": ret_dict
            })





def compose_response(json_data):
    values = json.loads(json_data)['values']
    
    # Prepare the Output before the loop
    results = {}
    results["values"] = []
    
    for value in values:
        output_record = transform_value(value)
        if output_record != None:
            results["values"].append(output_record)

    return json.dumps(results, ensure_ascii=False)

    


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        body = json.dumps(req.get_json())
    except ValueError:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )
    
    if body:
        result = compose_response(body)
        return func.HttpResponse(result, mimetype="application/json")
    else:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )


