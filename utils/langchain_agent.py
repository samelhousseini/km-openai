import os
import pickle
import numpy as np
import tiktoken
import json
import logging
import re
import copy
import uuid
import urllib

from langchain.llms.openai import AzureOpenAI
from langchain.agents import initialize_agent, Tool, load_tools, AgentExecutor
from langchain.llms import OpenAI
from langchain.prompts.prompt import PromptTemplate
from langchain import LLMMathChain
from langchain.prompts import PromptTemplate, BasePromptTemplate
from langchain.agents.mrkl.base import ZeroShotAgent
from typing import Any, Callable, List, NamedTuple, Optional, Sequence, Tuple
from langchain.tools.base import BaseTool
from langchain.schema import AgentAction, AgentFinish
from langchain.memory import ConversationBufferMemory
from datetime import datetime
from datetime import date
from langchain.agents import AgentType
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI

from utils.langchain_helpers.oldschoolsearch import OldSchoolSearch
from utils.langchain_helpers.mod_agent import GPT35TurboAzureOpenAI, ZSReAct, ReAct, ModBingSearchAPIWrapper, ModConversationalChatAgent
import utils.langchain_helpers.mod_react_prompt

from utils import openai_helpers
from utils.language import extract_entities
from utils import redis_helpers
from utils import storage

from utils.helpers import redis_search, redis_lookup
from utils.cogsearch_helpers import cog_search, cog_lookup
from multiprocessing.dummy import Pool as ThreadPool

from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
from utils.langchain_helpers import streaming_handler
from langchain.callbacks.base import CallbackManager


AZURE_OPENAI_SERVICE = os.environ.get("OPENAI_RESOURCE_ENDPOINT") 
OPENAI_API_KEY= os.environ.get("OPENAI_API_KEY")
DAVINCI_003_COMPLETIONS_MODEL = os.environ.get("DAVINCI_003_COMPLETIONS_MODEL")
CHOSEN_COMP_MODEL = os.environ.get("CHOSEN_COMP_MODEL")
COG_SEARCH_ENDPOINT= os.environ.get("COG_SEARCH_ENDPOINT")
COG_SEARCH_ADMIN_KEY= os.environ.get("COG_SEARCH_ADMIN_KEY")
KB_SEM_INDEX_NAME = os.environ.get("KB_SEM_INDEX_NAME")
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS"))
CHOSEN_EMB_MODEL = os.environ.get("CHOSEN_EMB_MODEL")
MAX_QUERY_TOKENS = int(os.environ.get("MAX_QUERY_TOKENS"))
MAX_HISTORY_TOKENS = int(os.environ.get("MAX_HISTORY_TOKENS"))
USE_BING = os.environ.get("USE_BING")
CONVERSATION_TTL_SECS = int(os.environ.get("CONVERSATION_TTL_SECS"))

import openai

openai.api_type = "azure"
openai.api_key = os.environ["OPENAI_API_KEY"]
openai.api_base = os.environ["OPENAI_RESOURCE_ENDPOINT"]


DEFAULT_RESPONSE = "Sorry, the question was not clear, or the information is not in the knowledge base. Please rephrase your question."



pool = ThreadPool(6)




class KMOAI_Agent():

    def __init__(self, agent_name = "zs", params_dict={}, verbose=False, stream=False, connection=None, force_redis = True):

        self.stream = stream
        self.connection = connection
        self.redis_filter_param = '*'
        self.cogsearch_filter_param = None
        self.agent_name = agent_name
        self.verbose = verbose
        self.history = ""

        self.enable_unified_search = params_dict.get('enable_unified_search', False)
        self.enable_cognitive_search = params_dict.get('enable_cognitive_search', False)
        self.enable_redis_search = params_dict.get('enable_redis_search', False)
        self.evaluate_step = params_dict.get('evaluate_step', False)
        self.check_adequacy = params_dict.get('check_adequacy', False)
        self.check_intent = params_dict.get('check_intent', False)
        self.use_calendar = params_dict.get('use_calendar', False)
        self.use_bing = params_dict.get('use_bing', False)

        if self.enable_unified_search == None: self.enable_unified_search = False
        if self.enable_cognitive_search == None: self.enable_cognitive_search = False
        if self.enable_redis_search == None: self.enable_redis_search = False
        if self.evaluate_step == None: self.evaluate_step = False
        if self.check_adequacy == None: self.check_adequacy = False
        if self.check_intent == None: self.check_intent = False
        if self.use_calendar == None: self.use_calendar = False
        if self.use_bing == None: self.use_bing = False

        if self.verbose: print("enable_unified_search", self.enable_unified_search)
        if self.verbose: print("enable_cognitive_search", self.enable_cognitive_search)
        if self.verbose: print("enable_redis_search", self.enable_redis_search)
        if self.verbose: print("evaluate_step", self.evaluate_step)
        if self.verbose: print("check_adequacy", self.check_adequacy)
        if self.verbose: print("check_intent", self.check_intent)
        if self.verbose: print("use_calendar", self.use_calendar)
        if self.verbose: print("use_bing", self.use_bing)



        if force_redis:
            if (self.enable_unified_search == False) and (self.enable_cognitive_search == False) and (self.enable_redis_search == False):
                self.enable_redis_search = True

        gen = openai_helpers.get_generation(CHOSEN_COMP_MODEL)

        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

        if connection == None:
            callbacks = [streaming_handler.StreamingStdOutCallbackHandler()]
        else:
            callbacks = [streaming_handler.StreamingSocketIOCallbackHandler(connection['socketio'], connection['connection_id'])]

        if (gen == 3) or (gen == 3.5):
            openai.api_version = "2022-12-01"    
            self.llm = GPT35TurboAzureOpenAI(deployment_name=CHOSEN_COMP_MODEL, temperature=0, openai_api_key=openai.api_key, max_retries=10, 
                                             request_timeout=30, stop=['<|im_end|>'], streaming=self.stream,
                                             callback_manager=CallbackManager(callbacks),
                                             max_tokens=MAX_OUTPUT_TOKENS, verbose = True)
        elif gen == 4:
            openai.api_version = "2023-03-15-preview"
            self.llm = ChatOpenAI(model_name=CHOSEN_COMP_MODEL, model=CHOSEN_COMP_MODEL, engine=CHOSEN_COMP_MODEL, 
                                  temperature=0, openai_api_key=openai.api_key, max_retries=10, streaming=self.stream,
                                  callback_manager=CallbackManager(callbacks),
                                  request_timeout=30, max_tokens=MAX_OUTPUT_TOKENS, verbose = True)
        else:
            assert False, f"Generation unknown for model {CHOSEN_COMP_MODEL}"

        self.gen = gen
        zs_tools = []

        if self.use_calendar:
            zs_tools += [
            Tool(name="Calendar", func=self.get_date, description="useful for when you need to get the current time and date to answer the question. USE ONLY IF THIS IS RELEVANT TO THE QUESTION.")
            ]

        if self.enable_unified_search: 
            zs_tools += [
                Tool(name="Unified Search", func=self.unified_search, description="useful for when you need to start a search to answer questions from the knowledge base")
            ]
        
        if self.enable_redis_search: 
            zs_tools += [
                Tool(name="Redis Search", func=self.agent_redis_search, description="useful for when you need to answer questions from the Redis system"),
            ]

        if self.enable_cognitive_search: 
            zs_tools += [
                Tool(name="Cognitive Search", func=self.agent_cog_search, description="useful for when you need to answer questions from the Cognitive system"),
                Tool(name="Cognitive Lookup", func=self.agent_cog_lookup, description="useful for when you need to lookup terms from the the Cognitive system"),            
            ]


        if self.use_bing or (USE_BING == 'yes'):
            self.bing_search = ModBingSearchAPIWrapper(k=10)
            zs_tools.append(Tool(name="Online Search", func=self.agent_bing_search, description='useful for when you need to answer questions about current events from the internet'),)
        else:
            self.bing_search = None

        ds_tools = [
            Tool(name="Search", func=self.unified_search, description="useful for when you need to answer questions"),
            Tool(name="Lookup", func=self.agent_cog_lookup, description="useful for when you need to lookup terms")
        ]


        self.zs_tools = zs_tools
        

        self.zs_agent = ZSReAct.from_llm_and_tools(self.llm, zs_tools)
        self.zs_chain = AgentExecutor.from_agent_and_tools(self.zs_agent, zs_tools, verbose=verbose, max_iterations = 6, early_stopping_method="generate")

        self.ds_agent = ReAct.from_llm_and_tools(self.llm, ds_tools)
        self.ds_chain = AgentExecutor.from_agent_and_tools(self.ds_agent, ds_tools, verbose=verbose, return_intermediate_steps = verbose, max_iterations = 6, early_stopping_method="generate", memory=self.memory )

                                          
        # self.ccrd_chain = initialize_agent(self.zs_tools, self.llm, agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION, verbose=True, memory=self.memory)

        # from langchain.agents.conversational_chat.base import ConversationalChatAgent
        self.ccrd_agent = ModConversationalChatAgent.from_llm_and_tools(self.llm, zs_tools)
        self.ccrd_chain =  AgentExecutor.from_agent_and_tools(self.ccrd_agent, zs_tools, verbose=verbose, max_iterations = 6, early_stopping_method="generate", memory=self.memory)

        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)

        zs_pr = self.zs_agent.create_prompt([]).format(input='', history='', agent_scratchpad='')
        ds_pr = self.ds_agent.create_prompt([]).format(history='', input='', agent_scratchpad='', pre_context='')

        self.zs_empty_prompt_length = len(completion_enc.encode(zs_pr))
        self.ds_empty_prompt_length = len(completion_enc.encode(ds_pr))



    def get_date(self, query):
        return f"Today's date and time {datetime.now().strftime('%A %B %d, %Y %H:%M:%S')}. You can use this date to derive the day and date for any time-related questions, such as this afternoon, this evening, today, tomorrow, this weekend or next week."


    def agent_redis_search(self, query):
        response = redis_helpers.redis_get(self.redis_conn, query, 'redis_search_response', verbose = self.verbose)

        if response is None:
            response = '\n\n'.join(redis_search(query, self.redis_filter_param))
            response = self.evaluate(query, response)
            redis_helpers.redis_set(self.redis_conn, query, 'redis_search_response', response, CONVERSATION_TTL_SECS, verbose = self.verbose)
        else:
            response = response.decode('UTF-8')

        return response


    def agent_redis_lookup(self, query):
        response = redis_helpers.redis_get(self.redis_conn, query, 'redis_lookup_response', verbose = self.verbose)

        if response is None:
            response = '\n\n'.join(redis_lookup(query, self.redis_filter_param))
            response = self.evaluate(query, response)
            redis_helpers.redis_set(self.redis_conn, query, 'redis_lookup_response', response, CONVERSATION_TTL_SECS, verbose = self.verbose)
        else:
            response = response.decode('UTF-8')

        return response


    def agent_cog_search(self, query):
        response = redis_helpers.redis_get(self.redis_conn, query, 'cog_search_response', verbose = self.verbose)

        if response is None:
            response = '\n\n'.join(cog_search(query, self.cogsearch_filter_param))
            response = self.evaluate(query, response)
            redis_helpers.redis_set(self.redis_conn, query, 'cog_search_response', response, CONVERSATION_TTL_SECS, verbose = self.verbose)
        else:
            response = response.decode('UTF-8')

        return response



    def agent_cog_lookup(self, query):
        response = redis_helpers.redis_get(self.redis_conn, query, 'cog_lookup_response', verbose = self.verbose)

        if response is None:
            response = '\n\n'.join(cog_lookup(query, self.cogsearch_filter_param))
            response = self.evaluate(query, response)
            redis_helpers.redis_set(self.redis_conn, query, 'cog_lookup_response', response, CONVERSATION_TTL_SECS, verbose = self.verbose)
        else:
            response = response.decode('UTF-8')

        return response


    def agent_bing_search(self, query):
        if self.use_bing or (USE_BING == 'yes'):
            response = redis_helpers.redis_get(self.redis_conn, query, 'bing_search_response', verbose = self.verbose)

            if response is None:
                response = '\n\n'.join(self.bing_search.run(query))
                response = self.evaluate(query, response)
                redis_helpers.redis_set(self.redis_conn, query, 'bing_search_response', response, CONVERSATION_TTL_SECS, verbose = self.verbose)
            else:
                response = response.decode('UTF-8')

            return response
        else:
            return ''


    def evaluate(self, query, context):

        if self.evaluate_step:
            completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
            max_comp_model_tokens = openai_helpers.get_model_max_tokens(CHOSEN_COMP_MODEL)

            query_len = len(completion_enc.encode(query))
            empty_prompt = len(completion_enc.encode(utils.langchain_helpers.mod_react_prompt.mod_evaluate_instructions.format(context = "", question = "", todays_time="", history="")))
            allowance = max_comp_model_tokens - empty_prompt - MAX_OUTPUT_TOKENS - query_len
            if self.verbose: print("Evaluate Call Tokens:", len(completion_enc.encode(context)), allowance)
            context = completion_enc.decode(completion_enc.encode(context)[:allowance]) 
            prompt = utils.langchain_helpers.mod_react_prompt.mod_evaluate_instructions.format(context = context, question = query, todays_time=self.get_date(""), history=self.history)
            if self.verbose: print("Evaluate OAI Call")
            response = openai_helpers.contact_openai(prompt, CHOSEN_COMP_MODEL, MAX_OUTPUT_TOKENS, verbose=self.verbose)
            response = response.replace("<|im_end|>", '')
        else:
            response = context

        response = response.replace("<|im_end|>", '')

        return response 

    def qc(self, query, answer):
        prompt = utils.langchain_helpers.mod_react_prompt.mod_qc_instructions.format(answer = answer, question = query)
        if self.verbose: print("QC OAI Call")
        response = openai_helpers.contact_openai(prompt, CHOSEN_COMP_MODEL, MAX_OUTPUT_TOKENS, verbose=self.verbose)
        response = response.strip().replace(',', '').replace('.', '').lower().replace("<|im_end|>", '')
        if self.verbose: print(f"Is the answer adequate: {response}")
        if response == "no": print(answer)
        return response 


    def chichat(self, query):
        prompt = utils.langchain_helpers.mod_react_prompt.mod_chit_chat_instructions.format(question = query)
        if self.verbose: print("Chitchat OAI Call")
        response = openai_helpers.contact_openai(prompt, CHOSEN_COMP_MODEL, MAX_OUTPUT_TOKENS, verbose=self.verbose)
        response = response.strip().replace(',', '').replace('.', '').lower().replace("<|im_end|>", '')
        return response 


    def unified_search(self, query):

        response = redis_helpers.redis_get(self.redis_conn, self.intent_output, 'response', verbose = self.verbose)

        if response is None:
            list_f = ['redis_search', 'cog_lookup', 'cog_search']
            list_q = [query for f in list_f]

            if USE_BING == 'yes':
                list_f += ['bing_lookup']
                list_q += [query]
            
            # print(list_f, list_q)

            results = pool.starmap(self.specific_search,  zip(list_q, list_f))

            max_items = max([len(r) for r in results])

            final_context = []
            context_dict = {}

            for i in range(max_items):
                for j in range(len(results)):
                    if i < len(results[j]): 
                        if results[j][i] not in context_dict:
                            context_dict[results[j][i]] = 1
                            final_context.append(results[j][i])

            response = '\n\n'.join(final_context)   
            response = self.evaluate(query, response)

            redis_helpers.redis_set(self.redis_conn, self.intent_output, 'response', response, CONVERSATION_TTL_SECS, verbose = self.verbose)
        else:
            response = response.decode('UTF-8')
 
        return response



    def specific_search(self, q, func_name):
        if func_name == "redis_search": return redis_search(q, self.redis_filter_param)
        if func_name == "cog_lookup": return cog_lookup(q, self.cogsearch_filter_param)
        if func_name == "cog_search": return cog_search(q, self.cogsearch_filter_param)

        if USE_BING == 'yes':
            if func_name == "bing_lookup": return self.bing_search.run(q)


    def replace_occurrences(self, answer, occ):
        matches = re.findall(occ, answer, re.DOTALL)            
        for m in matches:
            try:
                if isinstance(m, tuple): m = ' '.join(m).rstrip()
                answer = answer.replace(m, '')        
            except Exception as e:
                if self.verbose: print(m, occ, e)
        return answer

    def process_final_response(self, query, response):

        # print("Unprocessed response", response)

        if isinstance(response, str):
            answer = response
        else:    
            answer = response.get('output')

        occurences = [
            "Action:[\n\r\s]+(.*?)[\n]*[\n\r\s](.*)"
            "Action Input:[\s\r\n]+",
            "Action:[\s\r\n]+None needed?.",
            "Action:[\s\r\n]+None?.",
            "Action:[\s\r\n]+",
            "Action [\d]+:",
            "Action Input:",
            "Online Search:",
            "Thought [0-9]+:",
            "Observation [0-9]+:",
            "Final Answer:",
            "Final Answer",
            "Finish\[",
            "Human:",
            "AI:",
            "--",
            "###"
        ]

        for occ in occurences:
            answer = self.replace_occurrences(answer, occ)
            
        answer = answer.replace('<|im_end|>', '')

        tools_occurences = [
            'Redis Search',
            'Cognitive Search',
            'Online Search',
            'Calendar',
        ]

        for occ in tools_occurences:
            answer = answer.replace(occ, 'the knowledge base')

        sources = []
        likely_sources = []

        answer_with_sources = copy.deepcopy(answer)

        source_matches = re.findall(r'\((.*?)\)', answer)  
        source_matches += re.findall(r'\[(.*?)\]', answer)
        
        for s in source_matches:
            try:
                arr = s.split('/')
                sas_link = storage.create_sas_from_container_and_blob(arr[0], arr[1])
                sources.append(sas_link)
                answer = answer.replace('('+s+')', '')
                answer = answer.replace('['+s+']', '')
            except:
                if s.startswith("https://"): 
                    sources.append(s)
                    answer = answer.replace('('+s+')', '')
                    answer = answer.replace('['+s+']', '')
                elif s.startswith("http://"): 
                    sources.append(s)
                    answer = answer.replace('('+s+')', '')
                    answer = answer.replace('['+s+']', '')
                else: 
                    likely_sources.append(s)

        answer = answer.replace("[]", '')
        answer = answer.strip().rstrip()

        if answer == '':
            answer = DEFAULT_RESPONSE

        if (self.agent_name == 'os') or (self.agent_name == 'zs'):
            self.memory.save_context({"input": query}, {"output": answer_with_sources})

        return answer, sources, likely_sources



    def get_history(self, prompt_id):
        
        try:

            if len(self.memory.buffer) > 0:
                if (prompt_id is None) or (prompt_id == ''):
                    prompt_id = str(uuid.uuid4())
                return self.load_history_from_memory(), prompt_id

            if (prompt_id is None) or (prompt_id == ''):
                hist = ''
                prompt_id = str(uuid.uuid4())
            else:
                rhist = redis_helpers.redis_get(self.redis_conn, prompt_id, 'history', verbose = self.verbose)
                if rhist is None:
                    hist = ''
                else:
                    hist = rhist.decode('utf-8')
                    new_hist = hist.split('\n')
                    for i in range(len(new_hist)):
                        if new_hist[i] == '': continue
                        if new_hist[i].startswith('System: '): continue
                        if new_hist[i].startswith('AI: '): continue
                        self.memory.save_context({"input": new_hist[i].replace('Human: ', '')}, {"output": new_hist[i+1].replace('AI: ', '')})
                        if self.verbose: print("Saving Context:", ({"input": new_hist[i].replace('Human: ', '')}, {"output": new_hist[i+1].replace('AI: ', '')}))
        except:
            hist = ''
            prompt_id = str(uuid.uuid4())

        return hist, prompt_id
    

    def generate_history_messages(self, hist):
        messages = []
        new_hist = hist.split('\n')
        
        for m in new_hist:
            if m.startswith('AI: '):
                messages.append(AIMessage(content = m.replace('AI: ', '')))
            elif m.startswith('Human: '):
                messages.append(HumanMessage(content = m.replace('Human: ', '')))
            elif m.startswith('System: '):
                messages.append(SystemMessage(content = m.replace('System: ', '')))
            else:
                messages.append(HumanMessage(content = m.replace('Human: ', '')))

        if self.verbose: print("Chat History Messages", messages) #TODO
        return messages 


    def load_history_from_memory(self):
        hist = self.memory.load_memory_variables({})['chat_history']
        history = ''
        for m in hist:
            if isinstance(m, AIMessage):
                history += 'AI: ' + m.content + '\n'
            elif isinstance(m, HumanMessage):
                history += 'Human: ' + m.content + '\n'
            elif isinstance(m, SystemMessage):
                history += 'System: ' + m.content + '\n'
            else:
                history += 'Human: ' + m.content + '\n'

        return history.replace('<|im_end|>', '')



    def manage_history(self, hist, sources, prompt_id):
        hist = self.load_history_from_memory()
        if self.verbose: print("Generated new history", hist)

        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
        hist_enc = completion_enc.encode(hist)
        hist_enc_len = len(hist_enc)

        if hist_enc_len > MAX_HISTORY_TOKENS * 0.85:
            if self.verbose: print("Summarizing History")
            hist = openai_helpers.openai_summarize(hist, CHOSEN_COMP_MODEL).replace('<|im_end|>', '')

        if hist_enc_len > MAX_HISTORY_TOKENS:
            hist = completion_enc.decode(hist_enc[hist_enc_len - MAX_HISTORY_TOKENS :])

        redis_helpers.redis_set(self.redis_conn, prompt_id, 'history', hist, CONVERSATION_TTL_SECS, verbose = self.verbose)



    def inform_agent_input_lengths(self, agent, query, history, pre_context):
        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
        agent.query_length        = len(completion_enc.encode(query))
        agent.history_length      = len(completion_enc.encode(history))
        agent.pre_context_length  = len(completion_enc.encode(pre_context))


    def assign_filter_param(self, filter_param):

        if filter_param is None:
            self.redis_filter_param = '*'
            self.cogsearch_filter_param = None
        else:
            self.redis_filter_param = filter_param
            self.cogsearch_filter_param = filter_param


    def process_request(self, query, hist, pre_context):
        
        if self.verbose: print("agent_name", self.agent_name)
        
        try:
            if self.agent_name == 'ccr':
                response = self.ccrd_chain({'input':query})
            elif self.agent_name == 'zs':
                response = self.zs_chain({'input':query, 'history':hist})  
            elif self.agent_name == 'ds':                
                response = self.ds_chain({'input':query, 'history':hist, 'pre_context':pre_context})
            elif self.agent_name == 'os':   
                response = OldSchoolSearch().search(query, hist, pre_context, filter_param=self.redis_filter_param, 
                                                    enable_unified_search=self.enable_unified_search, lc_agent=self, 
                                                    enable_cognitive_search=self.enable_cognitive_search, evaluate_step=self.evaluate_step,
                                                    stream=self.stream, verbose=self.verbose)             
            else:
                response = self.zs_chain({'input':query, 'history':hist, 'pre_context':pre_context}) 


        except Exception as e:
            e_str = str(e)
            response = f"Technical Error: {e_str}"
            print("Exception", response)
            # assert False

            # if e_str.startswith("Could not parse LLM output:"):
            #     response = e_str.replace("Action: None", "").replace("Action:", "").replace('<|im_end|>', '')
            # else:
            #     print("Exception 2nd chain", e)
            #     try:
            #         response = self.zs_chain({'input':query, 'history':hist}) 
            #     except Exception as e:
            #         try:
            #             oss = OldSchoolSearch()
            #             response = oss.search(query, hist, pre_context, filter_param=self.redis_filter_param, 
            #                                     enable_unified_search=self.enable_unified_search, lc_agent=self, 
            #                                     enable_cognitive_search=self.enable_cognitive_search, evaluate_step=self.evaluate_step, 
            #                                     stream=stream)   
                    
            #         except Exception as e:
            #             print("Exception 3rd chain", e)
            #             try:
            #                 response = self.ds_chain({'input':query, 'history':hist, 'pre_context':pre_context})    
            #             except Exception as e:
            #                 print("Exception 4th chain", e)
            #                 response = DEFAULT_RESPONSE  

        
        if (self.agent_name == 'os') and (self.stream):
            ans = ""
            for resp in response:
                word = self.process_stream_response(resp)
                if word != '<|im_end|>':
                    if self.verbose: print(word, end='')
                    ans += word
                    if self.connection is not None:
                        self.connection['socketio'].emit('token', word.replace('\n', '<br>'), to=self.connection['connection_id'])
            response = ans

        return self.process_final_response(query, response)


    def get_pre_context(self, intent):
        
        if (intent is None) or (intent == ''):
            return ""
        else:
            pre_context = redis_helpers.redis_get(self.redis_conn, intent, 'answer', verbose = self.verbose)
            sources = redis_helpers.redis_get(self.redis_conn, intent, 'sources', verbose = self.verbose)

            if pre_context is None:
                return ""
            else:
                pre_context = pre_context.decode('utf-8')
                sources = sources.decode('utf-8')

        return f"[{sources}] {pre_context}"


    def get_intent(self, query):
        prompt = utils.langchain_helpers.mod_react_prompt.mod_extract_intent_instructions.format(question = query)
        if self.verbose: print("Intent OAI Call")
        response = openai_helpers.contact_openai(prompt, CHOSEN_COMP_MODEL, MAX_OUTPUT_TOKENS, verbose=self.verbose)

        output = response.strip().replace("<|im_end|>", '')

        intent_regex = "[iI]ntent:[\r\n\t\f\v ]+.*\n"
        output_regex = "[kK]eywords:[\r\n\t\f\v ]+.*"

        try:
            intent = re.search(intent_regex, output, re.DOTALL)
            keywords = re.search(output_regex, output, re.DOTALL)
            intent, keywords = intent.group(0).replace('\n', '').replace('Intent:', '').strip(), keywords.group(0).replace('\n', '').replace('Keywords:', '').strip()
            intent, keywords = intent.replace(',', '').strip(), keywords.replace(',', '').replace('.', '').strip()

            if self.verbose: print('\n', 'Intent:', intent.strip(), '\n', 'Response:', keywords)
            keywords = keywords.lower().split(' ')
            keywords = list(set(keywords))
            keywords = ' '.join(keywords)

            return intent.strip().lower(), keywords
        except:
            return 'knowledge base', None



    def process_stream_response(self, resp):
        if self.agent_name == 'os':
            if self.gen == 4:
                return str(resp["choices"][0]["delta"].get("content", ''))
            else:
                return resp["choices"][0]["text"]

        return resp



    def run(self, query, redis_conn, prompt_id = None, filter_param = None):

        self.redis_conn = redis_conn
        
        hist, prompt_id = self.get_history(prompt_id)
        self.history = hist.replace('\n', ' ')
        if self.verbose: print(f"Inserting history: {hist}")
        pre_context = ''
        self.intent_output = self.agent_name + ': ' + query

        if self.check_intent:
            if hist == '':
                intent, intent_output = self.get_intent(query)
            else:
                intent, intent_output = self.get_intent(self.history + '. ' + query)

            self.intent_output = self.agent_name + ': ' + intent_output
            if self.verbose: print("Intent:", intent, '-', self.intent_output)

            if intent == "chit chat":
                return self.chichat(query), [], [], prompt_id

        self.assign_filter_param(filter_param)
        self.inform_agent_input_lengths(self.zs_chain.agent, query, hist, pre_context)
        self.inform_agent_input_lengths(self.ds_chain.agent, query, hist, pre_context)

        answer, sources, likely_sources = self.process_request(query, hist, pre_context)

        if self.verbose: 
            print("************************")
            print("Final Answer:", answer)
            print("Sources:", sources)
            print("************************")

        if not self.check_adequacy:
            self.manage_history(hist, sources, prompt_id)
            return answer, sources, likely_sources, prompt_id
        
        tries = 3
        adequate = "no"

        if self.check_adequacy:
            while tries > 0:
                adequate = self.qc(query, answer)

                if adequate == "no":
                    answer, sources, likely_sources = self.process_request(query, hist, pre_context)
                    tries -= 1
                else:
                    break

            if adequate == "no":
                return DEFAULT_RESPONSE, [], [], prompt_id


        self.manage_history(hist, sources, prompt_id)
        return answer, sources, likely_sources, prompt_id
        





    def run_stream(self, query, prompt_id, redis_conn, filter_param, connection_id=None):

        self.redis_conn = redis_conn
        
        hist, prompt_id = self.get_history(prompt_id)
        self.history = hist.replace('\n', ' ')
        if self.verbose: print(f"Inserting history: {hist}")
        pre_context = ''
        self.intent_output = self.agent_name + ': ' + query

        if self.check_intent:
            intent, intent_output = self.get_intent(query)
            self.intent_output = self.agent_name + ': ' + intent_output
            if self.verbose: print("Intent:", intent, '-', self.intent_output)

            if intent == "chit chat":
                return self.chichat(query), [], [], prompt_id

            pre_context = self.get_pre_context(self.intent_output)
            if self.verbose: print(f"Inserting pre-context: {pre_context}")

        self.assign_filter_param(filter_param)

        if connection_id is not None:
            service = WebPubSubServiceClient.from_connection_string(connection_string=PUB_SUB_ENDPOINT, hub='oaiqnachat')

        
        response = OldSchoolSearch().search(query, hist, pre_context, filter_param=self.redis_filter_param, 
                                                    enable_unified_search=self.enable_unified_search, lc_agent=self, 
                                                    enable_cognitive_search=self.enable_cognitive_search, evaluate_step=self.evaluate_step,
                                                    stream = True)             

        answer = ""
        for resp in response:
            resp = self.process_stream_response(resp["choices"][0]["text"])
            answer += resp
            if connection_id is not None:
                service.send_to_connection( message = resp, connection_id = connection_id)
            else:
                if self.verbose: print(resp, end='')

        answer, sources, likely_sources = self.process_final_response(query, answer) 

        if self.verbose: 
            print("************************")
            print("Final Answer:", answer)
            print("Sources:", sources)
            print("************************")

        self.manage_history(hist, prompt_id)
        # redis_helpers.redis_set(self.redis_conn, self.intent_output, 'answer', answer, CONVERSATION_TTL_SECS)
        # redis_helpers.redis_set(self.redis_conn, self.intent_output, 'sources', ','.join(sources), CONVERSATION_TTL_SECS)
        if connection_id is not None:
            service.send_to_connection( message = sources, connection_id = connection_id)
        
        #return answer, sources, likely_sources, prompt_id


        






