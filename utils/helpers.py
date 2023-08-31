import os
import pickle
import re
import numpy as np
import tiktoken
import json
import logging
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.storage.blob import ContainerClient, __version__
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
import copy
from langchain.llms import AzureOpenAI
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.base import CallbackManager

from utils import language
from utils import storage
from utils import redis_helpers
from utils import openai_helpers
from utils.kb_doc import KB_Doc
from utils import cosmos_helpers
from utils.langchain_helpers import mod_agent

from utils.env_vars import *


def generate_embeddings(full_kbd_doc, embedding_model, max_emb_tokens, previous_max_tokens = 0, text_suffix = '',  gen_emb=True):
    
    emb_documents = []

    json_object = full_kbd_doc.get_dict()

    logging.info(f"Starting to generate embeddings with {embedding_model} and {max_emb_tokens} tokens")
    print(f"Starting to generate embeddings with {embedding_model} and {max_emb_tokens} tokens")

    try:
        if isinstance(json_object['timestamp'], list):
            json_object['timestamp'] = json_object['timestamp'][0]
        elif isinstance(json_object['timestamp'], str):
            json_object['timestamp'] = json_object['timestamp']
        else:
            json_object['timestamp'] = "1/1/1970 00:00:00 AM"    
    except:
        json_object['timestamp'] = "1/1/1970 00:00:00 AM"

    

    #### FOR DEMO PURPOSES ONLY -- OF COURSE NOT SECURE
    access = 'public'

    if (json_object['filename'] is None) or (json_object['filename'] == '')  or (json_object['filename'] == 'null'):
        filename = storage.get_filename(json_object['doc_url'])
    else:
        filename = json_object['filename']

    if filename.startswith('PRIVATE_'):
        access = 'private'
    #### FOR DEMO PURPOSES ONLY -- OF COURSE NOT SECURE


    doc_id = json_object['id']
    doc_text = json_object['text']
    enc = openai_helpers.get_encoder(embedding_model)
    tokens = enc.encode(doc_text)
    lang = language.detect_content_language(doc_text[:500])
    is_doc = json_object.get('doc_url', False) # doc_url empty for scraped webpages. web_url used instead.
    if is_doc:
        json_object['doc_url'] = storage.create_sas(json_object.get('doc_url', "https://microsoft.com"))
    else:
        json_object['doc_url'] = ''
    #  json_object['filename'] = filename
    json_object['access'] = access
    json_object['orig_lang'] = lang


    print("Comparing lengths", len(tokens) , previous_max_tokens-OVERLAP_TEXT)

    if (len(tokens) < previous_max_tokens-OVERLAP_TEXT) and (previous_max_tokens > 0):
        print("Skipping generating embeddings as it is optional for this text")
        return emb_documents


    suff = 0 
    for chunk in chunked_words(tokens, chunk_length=max_emb_tokens-OVERLAP_TEXT):
        decoded_chunk = enc.decode(chunk)
        
        translated_chunk = decoded_chunk
        if lang != 'en': 
            translated_chunk = language.translate(decoded_chunk, lang)
       
        if gen_emb:
            embedding = openai_helpers.get_openai_embedding(translated_chunk, embedding_model)
        else:
            embedding = ''

        dd = copy.deepcopy(json_object)
        dd['id'] = f"{doc_id}_{text_suffix}_{suff}"
        dd['text_en'] = translated_chunk
        if lang != 'en': dd['text'] = decoded_chunk
        else: dd['text'] = ''
        dd[VECTOR_FIELD_IN_REDIS] = embedding

        chunk_kbd_doc = KB_Doc()
        chunk_kbd_doc.load(dd)

        emb_documents.append(chunk_kbd_doc.get_dict())
        suff += 1

        if suff % 10 == 0:
            print (f'Processed: {suff} embeddings for document {filename}')
            logging.info (f'Processed: {suff} embeddings for document {filename}')


    print(f"This doc generated {suff} chunks")
    logging.info(f"This doc generated {suff} chunks")

    return emb_documents



def generate_embeddings_from_json_docs(json_folder, embedding_model, max_emb_tokens, text_suffix='M', limit = -1):
    
    emb_documents = []

    counter = 0
    for item in os.listdir(json_folder):
        if (limit != -1 ) and (counter >= limit): break
        path = os.path.join(json_folder, item)

        with open(path, 'r') as openfile:
            json_object = json.load(openfile)
        
        doc_embs = generate_embeddings(json_object, embedding_model, max_emb_tokens = max_emb_tokens, text_suffix = text_suffix)
        emb_documents += doc_embs
        counter += 1

        print(f"Now processing {path}, generated {len(doc_embs)} chunks")

    return emb_documents



def save_object_to_pkl(object, filename):
    with open(filename, 'wb') as pickle_out:
        pickle.dump(object, pickle_out)


def load_object_from_pkl(filename):
    with open(filename, 'rb') as pickle_in:
        object = pickle.load(pickle_in)

    return object  


def load_embedding_docs_in_redis(emb_documents, emb_filename = '', document_name = ''):

    if (emb_documents is None) and (emb_filename != ''):
        emb_documents = load_embedding_docs_from_pkl(emb_filename)

    redis_conn = redis_helpers.get_new_conn()

    print(f"Loading {len(emb_documents)} embeddings into Redis")
    logging.info(f"Loading {len(emb_documents)} embeddings into Redis")

    counter = 0
    loaded = 0

    for e in emb_documents:
        loaded += redis_helpers.redis_upsert_embedding(redis_conn, e)

        counter +=1
        if counter % 200 == 0:
            print (f'Processed: {counter} of {len(emb_documents)} for document {document_name}')
            logging.info (f'Processed: {counter} of {len(emb_documents)} for document {document_name}')
    
    print (f'Processed: {counter} of {len(emb_documents)} for document {document_name}')

    return loaded


def chunked_words(tokens, chunk_length, overlap=OVERLAP_TEXT):
    num_slices = len(tokens) // chunk_length + (len(tokens) % chunk_length > 0)
    chunks_iterator = (tokens[i*chunk_length:(i+1)*chunk_length + overlap] for i in range(num_slices))
    yield from chunks_iterator




def push_summarizations(doc_text, completion_model, max_output_tokens):
         
    for chunk in chunked_words(tokens, chunk_length=max_summ_tokens):
        print("Chunking summarization", len(chunk))
        d['summary'].append(openai_summarize(enc.decode(chunk), completion_model, max_output_tokens))
                
    summary = '\n'.join(d['summary'])
    logging.info(f"Summary {summary}")
    print(f"Summary {summary}")

    push_embeddings(summary, enc.encode(summary), lang,  timestamp, doc_id, doc_url, text_suffix = 'summ')



re_strs = [
    "customXml\/[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*", 
    "ppt\/[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*",
    "\.MsftOfcThm_[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*[\r\n\t\f\v ]\{[\r\n\t\f\v ].*[\r\n\t\f\v ]\}",
    "SlidePowerPoint",
    "PresentationPowerPoint",
    '[a-zA-Z0-9]*\.(?:gif|emf)'
    ]



def redis_search(query: str, filter_param: str):
    if (REDIS_ADDR is None) or (REDIS_ADDR == ''): 
        return ["Sorry, I couldn't find any information related to the question."]


    redis_conn = redis_helpers.get_new_conn()
    completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
    embedding_enc = openai_helpers.get_encoder(CHOSEN_EMB_MODEL)

    query = embedding_enc.decode(embedding_enc.encode(query)[:MAX_QUERY_TOKENS])

    query_embedding = openai_helpers.get_openai_embedding(query, CHOSEN_EMB_MODEL)    
    results = redis_helpers.redis_query_embedding_index(redis_conn, query_embedding, -1, topK=NUM_TOP_MATCHES, filter_param=filter_param)

    if len(results) == 0:
        logging.warning("No embeddings found in Redis, attempting to load embeddings from Cosmos")
        cosmos_helpers.cosmos_restore_embeddings()
        results = redis_helpers.redis_query_embedding_index(redis_conn, query_embedding, -1, topK=NUM_TOP_MATCHES, filter_param=filter_param)
    
    return process_search_results(results)
    
    
def process_search_results(results):
    completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)

    if len(results) == 0:
        return ["Sorry, I couldn't find any information related to the question."]

    context = []

    for t in results:
        t['text_en'] = t['text_en'].replace('\r', ' ').replace('\n', ' ') 

        try:
            if ('web_url' in t.keys()) and (t['web_url'] is not None) and (t['web_url'] != ''):
                context.append('\n\n' + f"[{t['web_url']}] " + t['text_en'] + '\n\n')
            else:
                context.append('\n\n' + f"[{t['container']}/{t['filename']}] " + t['text_en']  + '\n\n')
        except Exception as e:
            print("------------------- Exception in process_search_results: ", e)
            context.append('\n\n' + t['text_en'] + '\n\n')


    for i in range(len(context)):
        for re_str in re_strs:
            matches = re.findall(re_str, context[i], re.DOTALL)
            for m in matches: context[i] = context[i].replace(m, '')

    final_context = []
    total_tokens = 0

    for i in range(len(context)):
        total_tokens += len(completion_enc.encode(context[i]))
        # print(total_tokens)
        if  (total_tokens < MAX_SEARCH_TOKENS) and (len(final_context) < NUM_TOP_MATCHES):
            final_context.append(context[i])
        else:
            break

    return final_context


def redis_lookup(query: str, filter_param: str):
    redis_conn = redis_helpers.get_new_conn()
    completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)

    embedding_enc = openai_helpers.get_encoder(CHOSEN_EMB_MODEL)
    query = embedding_enc.decode(embedding_enc.encode(query)[:MAX_QUERY_TOKENS])

    query_embedding = openai_helpers.get_openai_embedding(query, CHOSEN_EMB_MODEL)    
    results = redis_helpers.redis_query_embedding_index(redis_conn, query_embedding, -1, topK=1, filter_param=filter_param)

    if len(results) == 0:
        logging.warning("No embeddings found in Redis, attempting to load embeddings from Cosmos")
        cosmos_helpers.cosmos_restore_embeddings()
        results = redis_helpers.redis_query_embedding_index(redis_conn, query_embedding, -1, topK=NUM_TOP_MATCHES, filter_param=filter_param)
        
    context = ' \n'.join([f"[{t['container']}/{t['filename']}] " + t['text_en'].replace('\n', ' ') for t in results])
    
    for re_str in re_strs:
        matches = re.findall(re_str, context, re.DOTALL)
        for m in matches: context = context.replace(m, '')

    context = completion_enc.decode(completion_enc.encode(context)[:MAX_SEARCH_TOKENS])
    return context





def get_llm(model = CHOSEN_COMP_MODEL, temperature=0.3, max_output_tokens=MAX_OUTPUT_TOKENS, stream=False, callbacks=[]):
    gen = openai_helpers.get_generation(model)

    if (gen == 3) :
        llm = AzureOpenAI(deployment_name=model, model_name=model, temperature=temperature, 
                        openai_api_key=openai.api_key, max_retries=30, 
                        request_timeout=120, streaming=stream,
                        callback_manager=CallbackManager(callbacks),
                        max_tokens=max_output_tokens, verbose = True)
                        
    elif (gen == 4) or (gen == 3.5):
        llm = ChatOpenAI(model_name=model, model=model, engine=model, 
                            temperature=0.3, openai_api_key=openai.api_key, max_retries=30, streaming=stream,
                            callback_manager=CallbackManager(callbacks),
                            request_timeout=120, max_tokens=max_output_tokens, verbose = True)    
    else:
        assert False, f"Generation unknown for model {model}"                                

    return llm                                  