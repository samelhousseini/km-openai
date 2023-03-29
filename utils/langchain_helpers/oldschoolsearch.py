
import openai
import tiktoken
import numpy as np
import os
import time
import logging
import re


from utils.langchain_helpers.simple_prompt import get_simple_prompt, append_tags, end_of_prev_prompt_tags

from utils import openai_helpers
from utils import redis_helpers
from utils import helpers


DAVINCI_003_MODEL_MAX_TOKENS = int(os.environ["DAVINCI_003_MODEL_MAX_TOKENS"])
ADA_002_MODEL_MAX_TOKENS     = int(os.environ["ADA_002_MODEL_MAX_TOKENS"])
DAVINCI_003_EMB_MAX_TOKENS   = int(os.environ['DAVINCI_003_EMB_MAX_TOKENS'])
GPT35_TURBO_COMPLETIONS_MODEL = os.environ['GPT35_TURBO_COMPLETIONS_MODEL']


CHOSEN_EMB_MODEL        = os.environ['CHOSEN_EMB_MODEL']
CHOSEN_QUERY_EMB_MODEL  = os.environ['CHOSEN_QUERY_EMB_MODEL']

NUM_TOP_MATCHES = int(os.environ['NUM_TOP_MATCHES'])
CHOSEN_COMP_MODEL = os.environ.get("CHOSEN_COMP_MODEL")
GPT35_TURBO_COMPLETIONS_MAX_TOKENS = int(os.environ.get("GPT35_TURBO_COMPLETIONS_MAX_TOKENS"))
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS"))
MAX_QUERY_TOKENS = int(os.environ.get("MAX_QUERY_TOKENS"))
MAX_HISTORY_TOKENS = int(os.environ.get("MAX_HISTORY_TOKENS"))
MAX_SEARCH_TOKENS  = int(os.environ.get("MAX_SEARCH_TOKENS"))
PRE_CONTEXT = int(os.environ['PRE_CONTEXT'])


redis_conn = redis_helpers.get_new_conn()

class OldSchoolSearch():


    def search(self, query, history, pre_context, filter_param=None,  enable_unified_search=False, lc_agent = None, enable_cognitive_search=False, evaluate_step=True, topK=NUM_TOP_MATCHES):   

        completion_model = CHOSEN_COMP_MODEL
        embedding_model = CHOSEN_EMB_MODEL

        completion_enc = openai_helpers.get_encoder(completion_model)
        embedding_enc = openai_helpers.get_encoder(embedding_model)

        max_comp_model_tokens = openai_helpers.get_model_max_tokens(completion_model)
        max_emb_model_tokens = openai_helpers.get_model_max_tokens(embedding_model)

        if enable_unified_search:
            context = lc_agent.unified_search(query)
        elif enable_cognitive_search:
            context = lc_agent.agent_cog_search(query, filter_param)
        else: 
            context = lc_agent.agent_redis_search(query)
        

        if (lc_agent is not None) and evaluate_step:
            context = lc_agent.evaluate(query, context)

        # print(context)
        query   = completion_enc.decode(completion_enc.encode(query)[:MAX_QUERY_TOKENS])
        history = completion_enc.decode(completion_enc.encode(history)[:MAX_HISTORY_TOKENS])
        pre_context = completion_enc.decode(completion_enc.encode(pre_context)[:PRE_CONTEXT])

        empty_prompt_length = len(completion_enc.encode(get_simple_prompt('', '', '', '')))
        context_length      = len(completion_enc.encode(context))
        query_length        = len(completion_enc.encode(query))
        history_length      = len(completion_enc.encode(history))
        pre_context_length  = len(completion_enc.encode(pre_context))

        max_context_len = max_comp_model_tokens - query_length - MAX_OUTPUT_TOKENS - empty_prompt_length - history_length - pre_context_length - 1

        context = completion_enc.decode(completion_enc.encode(context)[:max_context_len])
        
        prompt = get_simple_prompt(context, query, history, pre_context)  

        # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        # print(prompt)         
        # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

        final_answer = openai_helpers.contact_openai(prompt, completion_model, MAX_OUTPUT_TOKENS)

        return final_answer