import logging
import json
import azure.functions as func
import smart_open
import os, uuid
from azure.storage.blob import BlobServiceClient, BlobClient

from utils import helpers
from utils import cosmos_helpers
from utils import cogsearch_helpers
from utils.kb_doc import KB_Doc


KB_BLOB_CONN_STR = os.environ['KB_BLOB_CONN_STR']
OUTPUT_BLOB_CONTAINER = os.environ['OUTPUT_BLOB_CONTAINER']

ADA_002_EMBED_NUM_DIMS  = int(os.environ['ADA_002_EMBED_NUM_DIMS'])
ADA_002_MODEL_MAX_TOKENS  = int(os.environ['ADA_002_MODEL_MAX_TOKENS'])
ADA_002_EMBEDDING_MODEL   = os.environ['ADA_002_EMBEDDING_MODEL']

DAVINCI_003_EMBED_NUM_DIMS = int(os.environ['DAVINCI_003_EMBED_NUM_DIMS'])
DAVINCI_003_MODEL_MAX_TOKENS = int(os.environ['DAVINCI_003_MODEL_MAX_TOKENS'])
DAVINCI_003_COMPLETIONS_MODEL = os.environ['DAVINCI_003_COMPLETIONS_MODEL']
DAVINCI_003_EMBEDDING_MODEL   = os.environ['DAVINCI_003_EMBEDDING_MODEL']
DAVINCI_003_QUERY_EMB_MODEL   = os.environ['DAVINCI_003_QUERY_EMB_MODEL']

CHOSEN_EMB_MODEL   = os.environ['CHOSEN_EMB_MODEL']
SMALL_EMB_TOKEN_NUM  = int(os.environ['SMALL_EMB_TOKEN_NUM'])
MEDIUM_EMB_TOKEN_NUM  = int(os.environ['MEDIUM_EMB_TOKEN_NUM'])
LARGE_EMB_TOKEN_NUM  = int(os.environ['LARGE_EMB_TOKEN_NUM'])
X_LARGE_EMB_TOKEN_NUM = int(os.environ['X_LARGE_EMB_TOKEN_NUM'])

DATABASE_MODE = int(os.environ['DATABASE_MODE'])


def main(msg: func.ServiceBusMessage):

    msg_dict = json.loads(msg.get_body().decode('utf-8'))

    logging.info('Python ServiceBus queue trigger processed message: %s', msg_dict)
    logging.info("Event Type:%s", msg_dict['eventType'])

    transport_params = {
    'client': BlobServiceClient.from_connection_string(KB_BLOB_CONN_STR),
    }

    json_filename = os.path.basename(msg_dict['subject'])

    with smart_open.open(f"azure://{OUTPUT_BLOB_CONTAINER}/{json_filename}", transport_params=transport_params) as fin:
        data = json.load(fin)

    full_kbd_doc = KB_Doc()
    full_kbd_doc.load(data)

    # logging.info(data)

    emb_documents = []

    emb_documents += helpers.generate_embeddings(full_kbd_doc, CHOSEN_EMB_MODEL, SMALL_EMB_TOKEN_NUM,  text_suffix = 'S')

    if MEDIUM_EMB_TOKEN_NUM != 0:
        emb_documents += helpers.generate_embeddings(full_kbd_doc, CHOSEN_EMB_MODEL, MEDIUM_EMB_TOKEN_NUM, text_suffix = 'M', previous_max_tokens=SMALL_EMB_TOKEN_NUM)

    if LARGE_EMB_TOKEN_NUM != 0:
        emb_documents += helpers.generate_embeddings(full_kbd_doc, CHOSEN_EMB_MODEL, LARGE_EMB_TOKEN_NUM,  text_suffix = 'L', previous_max_tokens=MEDIUM_EMB_TOKEN_NUM)

    if X_LARGE_EMB_TOKEN_NUM != 0:
        emb_documents += helpers.generate_embeddings(full_kbd_doc, CHOSEN_EMB_MODEL, X_LARGE_EMB_TOKEN_NUM,  text_suffix = 'XL', previous_max_tokens=LARGE_EMB_TOKEN_NUM)

    if DATABASE_MODE == 1:
        cosmos_helpers.cosmos_backup_embeddings(emb_documents)
        
    cogsearch_helpers.index_semantic_sections(emb_documents)

    logging.info(f"Generated {len(emb_documents)} emb chunks from doc {json_filename}")

    loaded = helpers.load_embedding_docs_in_redis(emb_documents, document_name = json_filename)

    logging.info(f"Loaded into Redis {loaded} emb chunks from doc {json_filename}")
    