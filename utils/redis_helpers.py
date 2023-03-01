import os
import numpy as np
import redis
from redis import Redis
import logging
from redis.commands.search.field import VectorField
from redis.commands.search.field import TextField
from redis.commands.search.field import TagField
from redis.commands.search.query import Query
from redis.commands.search.result import Result


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
    redis_new_conn.ft(REDIS_INDEX_NAME).create_index([
        #VectorField(vector_field_name, "FLAT", {"TYPE": "FLOAT32", "DIM": vector_dimensions, "DISTANCE_METRIC": distance_metric, "INITIAL_CAP": number_of_vectors, "BLOCK_SIZE":number_of_vectors }),
        VectorField(vector_field_name, "HNSW", {"TYPE": "FLOAT32", "DIM": vector_dimensions, "DISTANCE_METRIC": distance_metric, "INITIAL_CAP": number_of_vectors, "M": M, "EF_CONSTRUCTION": EF}),
        TagField("id"),
        TextField("text"),
        TextField("text_en"),
        TextField("doc_url"),
        TagField("timestamp")        
    ])


def redis_reset_index(redis_new_conn):
    #flush all data
    redis_new_conn.flushall()

    #create flat index & load vectors
    create_search_index(redis_new_conn,VECTOR_FIELD_IN_REDIS, NUMBER_PRODUCTS_INDEX, get_model_dims(CHOSEN_EMB_MODEL), 'COSINE')


def test_redis(redis_new_conn):
    try:
        out = redis_new_conn.ft(REDIS_INDEX_NAME).info()
        print(f"Found Redis Index {REDIS_INDEX_NAME}")
    except Exception as e:
        print(f"Redis Index {REDIS_INDEX_NAME} not found. Creating a new index.")
        logging.error(f"Redis Index {REDIS_INDEX_NAME} not found. Creating a new index.")
        redis_reset_index(redis_new_conn)


def get_new_conn():
    if REDIS_PASSWORD == '':
        redis_conn = Redis(host = REDIS_ADDR, port = REDIS_PORT)
    else:
        redis_conn = redis.StrictRedis(host=REDIS_ADDR, port=int(REDIS_PORT), password=REDIS_PASSWORD, ssl=True)

    print('Connected to redis')
    test_redis(redis_conn)
    
    return redis_conn


def redis_upsert_embedding(redis_conn, e):     
    try:
        embeds = np.array(e['item_vector']).astype(np.float32).tobytes()
        meta = {'text_en': e['text_en'], 'text':e['text'], 'doc_url': e['doc_url'], 'timestamp': e['timestamp'], VECTOR_FIELD_IN_REDIS:embeds}
        p = redis_conn.pipeline(transaction=False)
        p.hset(e['id'], mapping=meta)
        p.execute()   
        return 1

    except Exception as e:
        print(f"Embedding Except: {e}")
        logging.error(f"Embedding Except: {e}")
        return 0




def redis_query_embedding_index(redis_conn, query_emb, t_id, topK=5):
   
    query_vector = np.array(query_emb).astype(np.float32).tobytes()
    q = Query(f'*=>[KNN {topK} @{VECTOR_FIELD_IN_REDIS} $vec_param AS vector_score]').sort_by('vector_score')\
                                .paging(0,topK).return_fields('vector_score','doc_url','text', 'text_en', 'timestamp').dialect(2)
    params_dict = {"vec_param": query_vector}
    results = redis_conn.ft(REDIS_INDEX_NAME).search(q, query_params = params_dict)
    
    return [{
                'id':match.id , 
                'text':match.text, 
                'text_en':match.text_en,
                'doc_url':match.doc_url,
                'timestamp':str(match.timestamp), 
                'score':match.vector_score
            } 
            for match in results.docs if match.id != t_id]





