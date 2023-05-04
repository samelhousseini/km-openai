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
from utils import km_agents

from utils.env_vars import *

        
redis_conn = redis_helpers.get_new_conn() 




def openai_interrogate_text(query, session_id=None, filter_param=None, agent_name=None, params_dict={}):

    lang = language.detect_content_language(query)
    if lang != 'en': query = language.translate(query, lang, 'en')

    if (agent_name is None) or (agent_name not in ['zs', 'ccr', 'os']):
        agent_name = 'zs'

    agent = km_agents.KMOAI_Agent(agent_name = agent_name, params_dict=params_dict, verbose = False)

    final_answer, sources, likely_sources, session_id = agent.run(query, redis_conn, session_id, filter_param)

    if lang != 'en': 
        final_answer = language.translate(final_answer, 'en', lang)
       
    sources_str = ', '.join(sources)

    ret_dict  = {
        "link": sources_str,
        "likely_links": likely_sources,
        "answer": final_answer,
        "context": '',
        "session_id": session_id
    }
    
    return json.dumps(ret_dict, indent=4) 
