import logging
import os
from flask import Flask, redirect, url_for, request, jsonify
from flask_socketio import SocketIO
from flask_socketio import send, emit
import urllib

from utils import bot_helpers
from utils import langchain_helpers
from utils import langchain_agent
from utils import redis_helpers


 
global_params_dict = {
    'enable_unified_search': True,
    'enable_redis_search': False,
    'enable_cognitive_search': False,
    'evaluate_step': False,
    'check_adequacy': False,
    'check_intent': False
}

redis_conn = redis_helpers.get_new_conn()


CHOSEN_EMB_MODEL   = os.environ['CHOSEN_EMB_MODEL']
CHOSEN_QUERY_EMB_MODEL   = os.environ['CHOSEN_QUERY_EMB_MODEL']
CHOSEN_COMP_MODEL   = os.environ['CHOSEN_COMP_MODEL']

DAVINCI_003_COMPLETIONS_MODEL = os.environ['DAVINCI_003_COMPLETIONS_MODEL']
NUM_TOP_MATCHES = int(os.environ['NUM_TOP_MATCHES'])

app = Flask(__name__)
socketio = SocketIO(app)
app.config['SECRET_KEY'] = 'secret!'


# source venv/bin/activate
# flask --app app.py --debug run

agents_sid = {}


@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path):
    print("path", path)
    return app.send_static_file(path)


@socketio.on('connect')
def on_connect():
    print(f"connected {request.sid}")


@socketio.on('config')
def on_config(agent_type):
    print(f"config {request.sid} - {agent_type}")
    connection = {'socketio': socketio, 'connection_id':request.sid}
    ccr_agent = langchain_agent.KMOAI_Agent(agent_name = agent_type, params_dict=global_params_dict,  stream = True, connection=connection)
    agents_sid[request.sid] = ccr_agent


@socketio.on('disconnect')
def on_disconnect():
    del agents_sid[request.sid]



@socketio.on('message')
def handle_message(q):
    print(f'received message: {q} from {request.sid}')
    emit('new_message', "Query: " + q + '\n') 
    answer, sources, likely_sources, s_id = agents_sid[request.sid].run(q, redis_conn, request.sid)
    sources_str = ''
    if len(sources) > 0:
        for s in sources: 
            try:
                linkname = urllib.parse.unquote(os.path.basename(s.split('?')[0]))
            except:
                linkname = 'Link'
            sources_str +=  '[<a href="' + s + f'" target="_blank">{linkname}</a>]' 
        send('Links:'+ sources_str)



##### IMPORTANT
##### INCLUDE IN THE POST HEADER --> Content-Type: application/json
##### IMPORTANT
@app.route('/kmoai_request', methods=['POST'])
def kmoai_request():
    data = request.get_json()
    return process_kmoai_request(data)



def check_param(param):
    if param == 'true':
        param = True
    else:
        param = False

    return param


def get_param(req, param_name):
    param = req.get(param_name, None) 
    return param



##### IMPORTANT
##### INCLUDE IN THE POST HEADER --> Content-Type: application/json
##### IMPORTANT
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
    use_calendar = get_param(req, 'use_calendar')
    use_bing = get_param(req, 'use_bing')

    params_dict = {
        'enable_unified_search': check_param(enable_unified_search),
        'enable_redis_search': check_param(enable_redis_search),
        'enable_cognitive_search': check_param(enable_cognitive_search),
        'evaluate_step': check_param(evaluate_step),
        'check_adequacy': check_param(check_adequacy),
        'check_intent': check_param(check_intent),
        'use_calendar': check_param(use_calendar),
        'use_bing': check_param(use_bing)
    }
    
    if filter_param is None:
        os.environ['redis_filter_param'] = '*'
    else:
        os.environ['redis_filter_param'] = filter_param

    return bot_helpers.openai_interrogate_text(query, session_id=session_id, filter_param=filter_param, agent_name=search_method, params_dict=params_dict)



if __name__ == '__main__':
    app.run()
    socketio.run(app, allow_unsafe_werkzeug=True)   
