import logging
import json
import re
import azure.functions as func
import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import ContainerClient
import urllib
import uuid
import copy

from utils import cosmos_helpers
from utils import storage
from utils import cv_helpers

from utils.env_vars import *


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
    ret_dict['status'] = ''
    db_status = ''
    data_dict['text'] = remove_urls(data_dict['content'].replace("\n\n\n", "\n").replace("....", "."))
    data_dict['contentType'] = 'text'
    data_dict['container'] = storage.get_container_name(data_dict['doc_url'])

    try:
        if isinstance(data_dict['timestamp'], list): 
            data_dict['timestamp'] = ' '.join(data_dict['timestamp'])
    except:
        data_dict['timestamp'] = "1/1/1970 00:00:00 AM"


        
    for re_str in re_strs:
        matches = re.findall(re_str, data_dict['text'], re.DOTALL)
        for m in matches: data_dict['text'] = data_dict['text'].replace(m, '')


    try:
        if PROCESS_IMAGES == 1:

            url = data_dict['doc_url']

            fn = storage.get_filename(url)
            extension = os.path.splitext(fn)[1]

            if extension in ['.jpg', '.jpeg', '.png']:
                sas_url = storage.create_sas(url)
                cvr = cv_helpers.CV()

                res = cvr.analyze_image(img_url=sas_url)

                data_dict['text'] = res['text'] + data_dict['text']
                data_dict['cv_image_vector'] = cvr.get_img_embedding(sas_url)
                data_dict['cv_text_vector'] = cvr.get_text_embedding(res['text'])
                data_dict['contentType'] = 'image'

    except Exception as e:    
        logging.error(f"Exception: Image {doc_id} created an exception.\n{e}")
        print(f"Exception: Image {doc_id} created an exception.\n{e}")
        ret_dict['status'] = f"Exception: Image {doc_id} created an exception.\n{e}"


    try:
        if DATABASE_MODE == 1:
            db_status = cosmos_helpers.cosmos_store_contents(data_dict)
            logging.info(db_status)
            print(db_status)
    except Exception as e:    
        doc_id = data_dict.get('id', 'Unknown ID')
        logging.error(f"Exception: Document {doc_id} created an exception.\n{e}")
        ret_dict['status'] = ret_dict['status'] + '\n' + f"Exception: Document {doc_id} created an exception.\n{e}"

    try:
        ret_dict = storage.save_json_document(data_dict, OUTPUT_BLOB_CONTAINER)
        logging.info(ret_dict['status'])
    except Exception as e:
        doc_id = data_dict.get('id', 'Unknown ID')
        logging.error(f"Exception: Document {doc_id} created an exception.\n{e}")
        ret_dict['status'] = ret_dict['status'] + '\n' + f"Exception: Document {doc_id} created an exception.\n{e}"

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


