import os
import pickle
import numpy as np
import tiktoken
import json
import logging
import re
import uuid

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
from langchain.utilities import BingSearchAPIWrapper


from utils.langchain_helpers.oldschoolsearch import OldSchoolSearch
from utils.langchain_helpers.mod_agent import GPT35TurboAzureOpenAI, ZSReAct, ReAct

from utils import openai_helpers
from utils.language import extract_entities

from utils.helpers import redis_search, redis_lookup
from utils.cogsearch_helpers import cog_search, cog_lookup


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
openai.api_version = "2022-12-01"

DEFAULT_RESPONSE = "Sorry, the question was not clear, or the information is not in the knowledge base. Please rephrase your question."

bing_search = BingSearchAPIWrapper()



class KMOAI_Agent():

    def __init__(self):

        self.redis_filter_param = '*'
        self.cogsearch_filter_param = None

        turbo_llm = GPT35TurboAzureOpenAI(deployment_name=CHOSEN_COMP_MODEL, temperature=0.0, openai_api_key=openai.api_key, max_retries=20, stop=['<|im_end|>'], max_tokens=MAX_OUTPUT_TOKENS)
        llm = AzureOpenAI(deployment_name=DAVINCI_003_COMPLETIONS_MODEL, temperature=0, openai_api_key=openai.api_key, max_retries=20, max_tokens=MAX_OUTPUT_TOKENS)
        llm_math = AzureOpenAI(deployment_name=DAVINCI_003_COMPLETIONS_MODEL, temperature=0, openai_api_key=openai.api_key, max_retries=20, max_tokens=MAX_OUTPUT_TOKENS)

        llm_math_chain = LLMMathChain(llm=llm, verbose=True)

        zs_tools = [
            Tool(name="Redis Search", func=self.agent_redis_search, description="useful for when you need to answer questions from the Redis system"),
            Tool(name="Redis Lookup", func=self.agent_redis_lookup, description="useful for when you need to lookup terms from the the Redis system"),
            Tool(name="Cognitive Search", func=self.agent_cog_search, description="useful for when you need to answer questions from the Cognitive system"),
            Tool(name="Cognitive Lookup", func=self.agent_cog_lookup, description="useful for when you need to lookup terms from the the Cognitive system"),            
            Tool(name="Calculator", func=llm_math_chain.run, description="useful for when you need to answer questions about math")
        ]


        if USE_BING == 'yes':
            zs_tools.append(Tool(name="Online Search", func=bing_search.run, description='useful for when you need to answer questions about current events from the internet'),)

        ds_tools = [
            Tool(name="Search", func=redis_search, description="useful for when you need to answer questions"),
            Tool(name="Lookup", func=cog_lookup, description="useful for when you need to lookup terms")
        ]


        self.memory = ConversationBufferMemory(memory_key="history")

        self.zs_agent = ZSReAct.from_llm_and_tools(turbo_llm, zs_tools)
        self.zs_chain = AgentExecutor.from_agent_and_tools(self.zs_agent, zs_tools, verbose=True, return_intermediate_steps = True, 
                                                                                                max_iterations = 10, early_stopping_method="generate" )

        self.ds_agent = ReAct.from_llm_and_tools(turbo_llm, ds_tools)
        self.ds_chain = AgentExecutor.from_agent_and_tools(self.ds_agent, ds_tools, verbose=True, return_intermediate_steps = True, 
                                                                                                max_iterations = 10, early_stopping_method="generate" )

        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)

        zs_pr = self.zs_agent.create_prompt([]).format(history='', input='', agent_scratchpad='', pre_context='')
        ds_pr = self.ds_agent.create_prompt([]).format(history='', input='', agent_scratchpad='', pre_context='')

        self.zs_empty_prompt_length = len(completion_enc.encode(zs_pr))
        self.ds_empty_prompt_length = len(completion_enc.encode(ds_pr))


    def agent_redis_search(self, query):
        return redis_search(query, self.redis_filter_param)


    def agent_redis_lookup(self, query):
        return redis_lookup(query, self.redis_filter_param)


    def agent_cog_search(self, query):
        return cog_search(query, self.cogsearch_filter_param)


    def agent_cog_lookup(self, query):
        return cog_lookup(query, self.cogsearch_filter_param)



    def replace_occurrences(self, answer, occ):
        matches = re.findall(occ, answer, re.DOTALL)            
        for m in matches:
            answer = answer.replace(m, '')        
        return answer

    def process_final_response(self, query, response):
        if isinstance(response, str):
            answer = response
        else:    
            answer = response.get('output')

        occurences = [
            "Action Input:[\s\r\n]+",
            "Action:[\s\r\n]+None needed?.",
            "Action:[\s\r\n]+None?.",
            "Action:[\s\r\n]+",
            "Action [\d]+:",
            "Observation [0-9]+:",
            "Final Answer:",
            "Final Answer",
            "Human:",
            "AI:",
        ]

        for occ in occurences:
            answer = self.replace_occurrences(answer, occ)
            
        answer = answer.replace('<|im_end|>', '')

        sources = []

        source_matches = re.findall(r'\[(.*?)\]', answer)  
        for s in source_matches:
            answer = answer.replace('['+s+']', '')
            sources.append(s)

        source_matches = re.findall(r'\((.*?)\)', answer)  
        for s in source_matches:
            answer = answer.replace('('+s+')', '')
            sources.append(s)

        answer = answer.strip().replace("\n", "")

        if answer == '':
            answer = DEFAULT_RESPONSE

        self.memory.save_context({"input": query}, {"output": answer})


        return answer, sources



    def get_history(self, prompt_id, redis_conn):

        if (prompt_id is None) or (prompt_id == ''):
            hist = ''
            prompt_id = str(uuid.uuid4())
            # prompt_id = "prompt_id"
            print("PROMPT ID", prompt_id)
        else:
            rhist = redis_conn.hget(prompt_id, 'history')
            if rhist is None:
                hist = ''
            else:
                hist = rhist.decode('utf-8')

        return hist, prompt_id
        

    def manage_history(self, hist, prompt_id, redis_conn):

        new_hist = self.memory.load_memory_variables({})['history']
        hist = hist + '\n' + new_hist
        
        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
        hist_enc = completion_enc.encode(hist)
        hist_enc_len = len(hist_enc)

        if hist_enc_len > MAX_HISTORY_TOKENS * 0.85:
            print("SUMMARIZING")
            hist = openai_helpers.openai_summarize(hist, CHOSEN_COMP_MODEL).replace('<|im_end|>', '')

        if hist_enc_len > MAX_HISTORY_TOKENS:
            hist = completion_enc.decode(hist_enc[hist_enc_len - MAX_HISTORY_TOKENS :])

        redis_conn.hset(prompt_id, 'history', hist)
        redis_conn.expire(name=prompt_id, time=CONVERSATION_TTL_SECS)



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



    def run(self, query, prompt_id, redis_conn, filter_param):

        hist, prompt_id = self.get_history(prompt_id, redis_conn)

        self.assign_filter_param(filter_param)

        entities = extract_entities(query)
        pre_context = []

        logging.info("Entities: " + str(entities))

        for entity in entities:
            try:
                logging.info("Searching for entity: " + entity)
                res = cog_lookup(entity)
                logging.info(f"CogLookup result: {res}")
                pre_context.append(res) 
            except Exception as e:
                logging.error(e)


        pre_context = '\n'.join(pre_context)
        print("pre_context", pre_context)  

        self.inform_agent_input_lengths(self.zs_chain.agent, query, hist, pre_context)
        self.inform_agent_input_lengths(self.ds_chain.agent, query, hist, pre_context)

        try:
            response = self.zs_chain({'input':query, 'history':hist, 'pre_context':pre_context}) 

        except Exception as e:
            e_str = str(e)

            if e_str.startswith("Could not parse LLM output:"):
                response = e_str.replace("Action: None", "").replace("Action:", "").replace('<|im_end|>', '')
            else:
                try:
                    response = self.ds_chain({'input':query, 'history':hist, 'pre_context':pre_context}) 
                except Exception as e:
                    try:
                        oss = OldSchoolSearch()
                        response = oss.search(query, hist, pre_context)
                    except Exception as e:
                        response = DEFAULT_RESPONSE  

        answer, sources = self.process_final_response(query, response)

        self.manage_history(hist, prompt_id, redis_conn)
        
        return answer, sources, prompt_id



        






