import logging
import os
from flask import Flask, redirect, url_for, request, jsonify
from flask_socketio import SocketIO
from flask_socketio import send, emit

import sys
sys.path.insert(0, '../')

from utils import bot_helpers


CHOSEN_EMB_MODEL   = os.environ['CHOSEN_EMB_MODEL']
CHOSEN_QUERY_EMB_MODEL   = os.environ['CHOSEN_QUERY_EMB_MODEL']
CHOSEN_COMP_MODEL   = os.environ['CHOSEN_COMP_MODEL']

DAVINCI_003_COMPLETIONS_MODEL = os.environ['DAVINCI_003_COMPLETIONS_MODEL']
NUM_TOP_MATCHES = int(os.environ['NUM_TOP_MATCHES'])

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# source venv/bin/activate
# flask --app app.py --debug run


@app.route("/")
def hello():
    print("hello there 3")
    return "<html><body><h1>Hello Enterprise Search with OpenAI Solution!</h1></body></html>\n"



@app.route('/kmoai_request', methods=['POST'])
def kmoai_request():
    data = request.get_json()
    return process_kmoai_request(data)



def check_param(param):
    if param == 'false':
        param = False
    else:
        param = True

    return param


def get_param(req, param_name):
    param = req.get(param_name, None) 
    return param


def process_kmoai_request(req):
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

    params_dict = {
        'enable_unified_search': check_param(enable_unified_search),
        'enable_redis_search': check_param(enable_redis_search),
        'enable_cognitive_search': check_param(enable_cognitive_search),
        'evaluate_step': check_param(evaluate_step),
        'check_adequacy': check_param(check_adequacy),
        'check_intent': check_param(check_intent)
    }
    
    if filter_param is None:
        os.environ['redis_filter_param'] = '*'
    else:
        os.environ['redis_filter_param'] = filter_param

    return bot_helpers.openai_interrogate_text(query, session_id=session_id, filter_param=filter_param, agent_name=search_method, params_dict=params_dict)
