import os
import numpy as np
import redis
from redis import Redis
import logging
import copy
from redis.commands.search.field import VectorField
from redis.commands.search.field import TextField
from redis.commands.search.field import TagField
from redis.commands.search.query import Query
from redis.commands.search.result import Result


## https://redis-py.readthedocs.io/en/stable/commands.html
## https://redis.io/docs/stack/search/reference/query_syntax/



from utils.kb_doc import KB_Doc

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)



REDIS_ADDR = os.environ["REDIS_ADDR"]   
REDIS_PORT = os.environ["REDIS_PORT"]   
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]   
REDIS_INDEX_NAME = os.environ["REDIS_INDEX_NAME"]   
VECTOR_FIELD_IN_REDIS = os.environ["VECTOR_FIELD_IN_REDIS"]   
NUMBER_PRODUCTS_INDEX = int(os.environ["NUMBER_PRODUCTS_INDEX"])
DAVINCI_003_EMBED_NUM_DIMS = int(os.environ['DAVINCI_003_EMBED_NUM_DIMS'])
ADA_002_EMBED_NUM_DIMS  = int(os.environ['ADA_002_EMBED_NUM_DIMS'])
CHOSEN_EMB_MODEL   = os.environ['CHOSEN_EMB_MODEL']




def get_model_dims(embedding_model):
    if embedding_model == "text-search-davinci-doc-001":
        return DAVINCI_003_EMBED_NUM_DIMS
    elif embedding_model == "text-embedding-ada-002":
        return ADA_002_EMBED_NUM_DIMS
    else:
        return ADA_002_EMBED_NUM_DIMS


def create_search_index (redis_new_conn, vector_field_name, number_of_vectors, vector_dimensions=512, distance_metric='L2'):
    M=40
    EF=200

    fields = [VectorField(vector_field_name, "HNSW", {"TYPE": "FLOAT32", "DIM": vector_dimensions, "DISTANCE_METRIC": distance_metric, "INITIAL_CAP": number_of_vectors, "M": M, "EF_CONSTRUCTION": EF})] + \
             [TextField(f) for f in KB_Doc().get_fields() if f != VECTOR_FIELD_IN_REDIS]

    redis_new_conn.ft(REDIS_INDEX_NAME).create_index(fields)


def redis_reset_index(redis_new_conn):
    #flush all data
    redis_new_conn.flushall()

    #create flat index & load vectors
    create_search_index(redis_new_conn,VECTOR_FIELD_IN_REDIS, NUMBER_PRODUCTS_INDEX, get_model_dims(CHOSEN_EMB_MODEL), 'COSINE')


def test_redis(redis_new_conn):
    try:
        out = redis_new_conn.ft(REDIS_INDEX_NAME).info()
        # print(f"Found Redis Index {REDIS_INDEX_NAME}")
    except Exception as e:
        # print(f"Redis Index {REDIS_INDEX_NAME} not found. Creating a new index.")
        logging.error(f"Redis Index {REDIS_INDEX_NAME} not found. Creating a new index.")
        redis_reset_index(redis_new_conn)


def get_new_conn():
    if REDIS_PASSWORD == '':
        redis_conn = Redis(host = REDIS_ADDR, port = REDIS_PORT)
    else:
        redis_conn = redis.StrictRedis(host=REDIS_ADDR, port=int(REDIS_PORT), password=REDIS_PASSWORD, ssl=True)

    #print('Connected to redis', redis_conn)
    test_redis(redis_conn)
    
    return redis_conn


retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(4))
def redis_upsert_embedding(redis_conn, e_dict):     
    try:
        #embeds = np.array(e[VECTOR_FIELD_IN_REDIS]).astype(np.float32).tobytes()
        #meta = {'text_en': e['text_en'], 'text':e['text'], 'doc_url': e['doc_url'], 'timestamp': e['timestamp'], VECTOR_FIELD_IN_REDIS:embeds}
        e = copy.deepcopy(e_dict)
        e[VECTOR_FIELD_IN_REDIS] = np.array(e[VECTOR_FIELD_IN_REDIS]).astype(np.float32).tobytes()

        p = redis_conn.pipeline(transaction=False)
        p.hset(e['id'], mapping=e)
        p.execute()   
        return 1

    except Exception as e:
        print(f"Embedding Except: {e}")
        logging.error(f"Embedding Except: {e}")
        return 0



@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(4))
def redis_query_embedding_index(redis_conn, query_emb, t_id, topK=5, filter_param=None):
   
    if (filter_param is None) or (filter_param == '*'):
        filter_param = '*'
    else:
        if not filter_param.startswith('@'):
            filter_param = '@' + filter_param

    filter_param = filter_param.replace('-', '\-')
    fields = list(KB_Doc().get_fields()) + ['vector_score']
    
    query_vector = np.array(query_emb).astype(np.float32).tobytes()
    
    query_string = f'({filter_param})=>[KNN {topK} @{VECTOR_FIELD_IN_REDIS} $vec_param AS vector_score]'
    # print('\n', query_string, filter_param, '\n')

    q = Query(query_string).sort_by('vector_score').paging(0,topK).return_fields(*fields).dialect(2)
    params_dict = {"vec_param": query_vector}
    
    results = redis_conn.ft(REDIS_INDEX_NAME).search(q, query_params = params_dict)
    
    return [{k: match.__dict__[k] for k in (set(list(match.__dict__.keys())) - set([VECTOR_FIELD_IN_REDIS]))} for match in results.docs if match.id != t_id]





@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(4))
def redis_set(redis_conn, key, field, value, expiry = None):
    try:
        key = key.replace('"', '')
        res = redis_conn.hset(key, field, value)

        if expiry is not None:
            redis_conn.expire(name=key, time=expiry)
        print("Setting Redis Key: ", key, field, expiry)
        return res
        
    except Exception as e:
        logging.error(f"Redis Set Except: {e}")
        print(f"Redis Set Except: {e}")
        return 0


@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(4))
def redis_get(redis_conn, key, field):
    try:
        key = key.replace('"', '')
        print("Getting Redis Key: ", key, field)
        return redis_conn.hget(key, field)
        
    except Exception as e:
        logging.error(f"Redis Get Except: {e}")
        print(f"Redis Get Except: {e}")
        return None

 