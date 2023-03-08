import logging
import json
import re
import azure.functions as func
import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import ContainerClient
import urllib
import uuid


DATABASE_MODE = os.environ['DATABASE_MODE']
COSMOS_URI  = os.environ['COSMOS_URI']
COSMOS_KEY  = os.environ['COSMOS_KEY']
COSMOS_DB_NAME   = os.environ['COSMOS_DB_NAME']
CATEGORYID  = os.environ['CATEGORYID']

KB_BLOB_CONN_STR = os.environ['KB_BLOB_CONN_STR']
OUTPUT_BLOB_CONTAINER = os.environ['OUTPUT_BLOB_CONTAINER']


def remove_urls(text):
    text = re.sub(r'(https|http)?:\/\/(\w|\.|\/|\?|\=|\&|\%)*\b', '', text, flags=re.MULTILINE)
    return text



def analyze_doc(data_dict):
    
    ret_dict = {}

    doc_id = data_dict.get('id', str(uuid.uuid4()))
    cs_doc = data_dict['content']
    timestamp = data_dict.get('timestamp', "1/1/1970 00:00:00 AM"), 
    doc_url = data_dict.get('doc_url', 'https://microsoft.com')
    doc_text = remove_urls(cs_doc.replace("\n\n", " ").replace("....", " ")).replace("\n\n", " ")

    new_doc = {
        "id": doc_id,
        "categoryId": CATEGORYID,
        "timestamp": timestamp,
        "doc_url": doc_url,
        "text": doc_text 
    }

    try:
        if DATABASE_MODE == '1':
            client = CosmosClient(url=COSMOS_URI, credential=COSMOS_KEY)
            partitionKeyPath = PartitionKey(path="/categoryId")
            database = client.create_database_if_not_exists(id=COSMOS_DB_NAME)
            container = database.create_container_if_not_exists(id="documents", partition_key=partitionKeyPath)
            container.upsert_item(new_doc)
            ret_dict['status'] = f"Document {doc_id} was successfully inserted into Cosmos"
            logging.info(ret_dict['status'])
            
        else:
            container = ContainerClient.from_connection_string(KB_BLOB_CONN_STR, OUTPUT_BLOB_CONTAINER)

            try:
                container_properties = container.get_container_properties()
            except Exception as e:
                container.create_container()

            blob_name = urllib.parse.unquote(os.path.basename(doc_url.split('?')[0]))
            pre, ext = os.path.splitext(blob_name)
            blob_name = pre + '.json'            
            blob_client = container.get_blob_client(blob=blob_name)
            blob_client.upload_blob(json.dumps(new_doc, indent=4), overwrite=True)
            ret_dict['status'] = f"Document {doc_id} was successfully saved to the {OUTPUT_BLOB_CONTAINER} container"
            logging.info(ret_dict['status'])

    except Exception as e:
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


