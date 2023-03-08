import logging
import azure.functions as func
import os

from utils import bot_helpers


CHOSEN_EMB_MODEL   = os.environ['CHOSEN_EMB_MODEL']
CHOSEN_QUERY_EMB_MODEL   = os.environ['CHOSEN_QUERY_EMB_MODEL']
CHOSEN_COMP_MODEL   = os.environ['CHOSEN_COMP_MODEL']

DAVINCI_003_COMPLETIONS_MODEL = os.environ['DAVINCI_003_COMPLETIONS_MODEL']
NUM_TOP_MATCHES = int(os.environ['NUM_TOP_MATCHES'])


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    query = req.params.get('query') 

    if not query:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            query = req_body.get('query')

    if query:
        str = bot_helpers.openai_interrogate_text(query, CHOSEN_COMP_MODEL, CHOSEN_QUERY_EMB_MODEL, NUM_TOP_MATCHES)
        return func.HttpResponse(str)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
