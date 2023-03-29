import logging
import azure.functions as func
import os

from utils import bot_helpers


CHOSEN_EMB_MODEL   = os.environ['CHOSEN_EMB_MODEL']
CHOSEN_QUERY_EMB_MODEL   = os.environ['CHOSEN_QUERY_EMB_MODEL']
CHOSEN_COMP_MODEL   = os.environ['CHOSEN_COMP_MODEL']

DAVINCI_003_COMPLETIONS_MODEL = os.environ['DAVINCI_003_COMPLETIONS_MODEL']
NUM_TOP_MATCHES = int(os.environ['NUM_TOP_MATCHES'])


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




def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    query = get_param(req, 'query')
    session_id = get_param(req, 'session_id')
    filter_param = get_param(req, 'filter')
    search_method = get_param(req, 'search_method')
    
    if filter_param is None:
        os.environ['redis_filter_param'] = '*'
    else:
        os.environ['redis_filter_param'] = filter_param

    if query:
        str = bot_helpers.openai_interrogate_text(query, session_id=session_id, filter_param=filter_param, agent_name=search_method)
        return func.HttpResponse(str)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
