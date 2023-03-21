import os
import pickle
import numpy as np
import tiktoken
import json
import logging


from utils import language
from utils import storage
from utils import redis_helpers
from utils import openai_helpers
from utils import cosmos_helpers
from utils import langchain_agent


MAX_QUERY_TOKENS             = int(os.environ["MAX_QUERY_TOKENS"])
MAX_OUTPUT_TOKENS            = int(os.environ["MAX_OUTPUT_TOKENS"])

DAVINCI_003_MODEL_MAX_TOKENS = int(os.environ["DAVINCI_003_MODEL_MAX_TOKENS"])
ADA_002_MODEL_MAX_TOKENS     = int(os.environ["ADA_002_MODEL_MAX_TOKENS"])
DAVINCI_003_EMB_MAX_TOKENS   = int(os.environ['DAVINCI_003_EMB_MAX_TOKENS'])


GPT35_TURBO_COMPLETIONS_MODEL = os.environ['GPT35_TURBO_COMPLETIONS_MODEL']
GPT35_TURBO_COMPLETIONS_MAX_TOKENS = int(os.environ["GPT35_TURBO_COMPLETIONS_MAX_TOKENS"])

CHOSEN_EMB_MODEL        = os.environ['CHOSEN_EMB_MODEL']
CHOSEN_QUERY_EMB_MODEL  = os.environ['CHOSEN_QUERY_EMB_MODEL']
CHOSEN_COMP_MODEL       = os.environ['CHOSEN_COMP_MODEL']

RESTRICTIVE_PROMPT    = os.environ['RESTRICTIVE_PROMPT']

        
redis_conn = redis_helpers.get_new_conn() 





def openai_interrogate_text(query, session_id=None, filter_param=None):

    lang = language.detect_content_language(query)
    if lang != 'en': query = language.translate(query, lang, 'en')

    agent = langchain_agent.KMOAI_Agent()

    final_answer, sources, session_id = agent.run(query, session_id, redis_conn, filter_param)

    if lang != 'en': 
        final_answer = language.translate(final_answer, 'en', lang)
       
    sources_str = ', '.join(sources)

    ret_dict  = {
        "link": sources_str,
        "answer": final_answer,
        "context": '',
        "session_id": session_id
    }
    
    return json.dumps(ret_dict, indent=4) 