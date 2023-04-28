import logging
import azure.functions as func
import os

from utils import bot_helpers

from utils.env_vars import *


def get_param(req, param_name):
    param = req.params.get(param_name) 

    if not param:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            param = req_body.get(param_name)
    
    return param



def check_param(param):
    if param == 'true':
        param = True
    else:
        param = False

    return param



def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    query = get_param(req, 'query')
    session_id = get_param(req, 'session_id')
    filter_param = get_param(req, 'filter')
    search_method = get_param(req, 'search_method')

    enable_unified_search = get_param(req, 'enable_unified_search')
    enable_redis_search = get_param(req, 'enable_redis_search')
    enable_cognitive_search = get_param(req, 'enable_cognitive_search')
    evaluate_step = get_param(req, 'evaluate_step')
    check_adequacy = get_param(req, 'check_adequacy')
    check_intent = get_param(req, 'check_intent') 
    use_calendar = get_param(req, 'use_calendar')
    use_calculator = get_param(req, 'use_calculator')
    use_bing = get_param(req, 'use_bing')
    

    params_dict = {
        'enable_unified_search': check_param(enable_unified_search),
        'enable_redis_search': check_param(enable_redis_search),
        'enable_cognitive_search': check_param(enable_cognitive_search),
        'evaluate_step': check_param(evaluate_step),
        'check_adequacy': check_param(check_adequacy),
        'check_intent': check_param(check_intent),
        'use_calendar': check_param(use_calendar),
        'use_calculator': check_param(use_calculator),
        'use_bing': check_param(use_bing)
    }

    if filter_param is None: filter_param = '*'

    if query:
        str = bot_helpers.openai_interrogate_text(query, session_id=session_id, filter_param=filter_param, agent_name=search_method, params_dict=params_dict)
        return func.HttpResponse(str)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
