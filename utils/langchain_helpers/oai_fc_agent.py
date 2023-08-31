import openai
import os
import json
import yaml
import copy
import numpy as np
import itertools


from utils.env_vars import *
from utils import openai_helpers
from utils import http_helpers
from utils.cogsearch_helpers import *


instruction_prompt =  """You are an AI assistant specialized in answering user questions about Hexagon products. You can call functions to obtain specific details based on user queries. 
Facts have sources, you MUST include the source name in the answer at the beginning before any text. If there are multiple sources, cite each one in their own square brackets. For example, use \"[folder3/info343][http://wikipedia.com]\" and not \"[folder3/info343,http://wikipedia.com]\". You must follow the following format strictly for the final answer: 
Answer: [folder1/file1][http://website][http://website2] the answer based on the facts or information.
DO NOT MAKE UP ANY ANSWERS, ALL ANSWERS MUST BE BASED ON THE CONTEXT WHICH IS DELIMITED BY 3 "AT SYMBOL". The Assistant should not make up sources. ALL SOURCES MUST BE EXTRACTED FROM THE CONTEXT WHICH IS DELIMITED BY 3 "AT SYMBOL".

The below are examples of final answers:

Question: "what is mentioned about the Lost City hotel?"
Answer: "The Lost City Hotel is a luxurious accommodation in Dubai with an onsite waterpark and aquarium. [website]"

Question: "what hotels are recommended in Las Vegas?"
Answer: "Margie's Travel offers the following hotels in Las Vegas: The Volcano Hotel, The Fountain Hotel, The Canal Hotel. To book your trip to Las Vegas, visit www.margiestravel.com. [folder/Las Vegas.pdf]"

Question: "who is Barack Obama?"
Answer: 'Barack Obama is the 44th President of the United States of America. [http://website]'

Question: "who is Barack Obama?"
Answer: 'Unfortunately, none of the sources I searched provided any specific information about Barack Obama. []'

Question: "how much are the one day pass tickets for Ferrari world?"
Answer: "I'm sorry, I could not find the ticket prices for Ferrari World. []

THE ASSISTANT MUST STRICTLY USE THE COLLECTED EVIDENCE FROM THE USER INPUT OR THE CONTEXT WHICH IS DELIMITED BY 3 "AT SYMBOL", THE ASSISTANT MUST NOT ANSWER FROM MEMORY AND MUST NOT MAKE UP ANSWERS. Assistant must make sure to send the correct source as a reference, if the source is already included in the history which is delimited by three dollar signs, make sure to include it again in the answer. The Assistant should not make up sources. ALL SOURCES MUST BE EXTRACTED FROM THE CONTEXT WHICH IS DELIMITED BY 3 "AT SYMBOL".
"""

intent_messages= [
    {"role": "system", "content":instruction_prompt},
]




# intent_functions= [  
#     {  
#         "name": "search_knowledge_base",  
#         "type": "function",  
#         "description": "Search through knowledge base to find relevant documents that might help in answering the user query.",  
#         "parameters": {  
#             "type": "object",  
#             "properties": {  
#                 "search_terms": {
#                     "type": "string",
#                     "description": "Search terms that would be used in the search engine"
#                 }
#             },  
#             "required": ["search_terms"]  
#         }  
#     }  
# ]  

intent_functions= [  
    {  
        "name": "extract_search_terms",  
        "type": "function",  
        "description": "Search through knowledge base to find relevant documents that might help in answering the user query.",  
        "parameters": {  
            "type": "object",  
            "properties": {  
                "search_terms": {  
                    "type": "array",  
                    "items": {  
                        "type": "object",  
                        "properties": {  
                            "term": {"type": "string",  "description": "Search terms that would be used in the search engine"  },  
                            "additional_context": {"type": "string",  "description": "Additional context related to the term."  },
                        },  
                        "required": ["term", "additional_context"]  
                    }  
                }
            },  
            "required": ["search_terms"]  
        }  
    }  
]  



intent_body = """
Current Conversation: 
$$$
{history}
$$$

Query: {query}       

"""


body = """
Current Conversation: 
$$$
{history}
$$$

Context: 
@@@
{context}
@@@

Question: {query}       

Answer:
"""



class oai_fc_agent():

    def __init__(self):
        self.context = {}
        self.context['history'] = ""
        


    def get_dict(self, response):
        dd = yaml.full_load(str(response['choices'][0]['message']))

        if 'function_call' in dd:
            dd['function_call']['arguments'] = yaml.full_load(dd['function_call']['arguments'])
        
        return dd


    def update_history(self, input_text, answer):
        self.context["history"] += f"\nUser: {input_text}\nChatBot: {answer}\n"


    def chat(self, query, lc_agent, history):
        search_results = []
        content = ""
        messages = copy.deepcopy(intent_messages)
        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)

        messages.append({"role": "user", "content":intent_body.format(history=history, query=query)})
        print("messages", messages)
        # messages.append({"role": "user", "content": query})
        response = openai_helpers.contact_openai(messages, completion_model = CHOSEN_COMP_MODEL, functions=intent_functions)

        dd = self.get_dict(response)
        print(dd)

        if 'function_call' in dd:
            search_terms  = dd['function_call']['arguments']['search_terms']
            search_results = [] 

            print("search_terms", search_terms)

            # search_results.append(lc_agent.agent_cog_search(search_terms))

            for s in search_terms:
                search_results.append(lc_agent.agent_cog_search(s['term'] + ' ' + s.get('additional_context', '')))
            
            search_results = '\n'.join(search_results)
   
            empty_prompt_length = len(completion_enc.encode(instruction_prompt + body))
            max_comp_model_tokens = openai_helpers.get_model_max_tokens(CHOSEN_COMP_MODEL)
            query   = completion_enc.decode(completion_enc.encode(query)[:MAX_QUERY_TOKENS])
            print("hi34")
            history = completion_enc.decode(completion_enc.encode(history)[:MAX_HISTORY_TOKENS])
            query_length        = len(completion_enc.encode(query))
            history_length      = len(completion_enc.encode(history))

            max_context_len = max_comp_model_tokens - query_length - MAX_OUTPUT_TOKENS - empty_prompt_length - history_length - 1

            print("max_context_len", max_context_len)
            context = completion_enc.decode(completion_enc.encode(search_results)[:max_context_len])


            messages.append(  # adding assistant response to messages
                    {
                    "role": dd["role"],
                    "name": dd["function_call"]["name"],
                    "content": str(dd['function_call']['arguments']['search_terms'])
                    }
            )
            messages.append(
                    {
                    "role": "function",
                    "name": dd["function_call"]["name"],
                    "content": str(search_results),
                    }
            )

            messages.append({"role": "user", "content":body.format(history=history, context=search_results, query=query)})

            print("search_results", len(search_results), search_results)
            answer = openai_helpers.contact_openai(messages, completion_model = CHOSEN_COMP_MODEL, functions=intent_functions)
            answer = answer['choices'][0]['message']['content']

        
        else:
            answer = dd['content']

        return answer


    # def final_call(self, query, search_results, history):
    #     messages = copy.deepcopy(final_call_messages)
    #     messages.append({"role": "user", "content":body.format(history=history, context=search_results, query=query)})
    #     response = openai_helpers.contact_openai(messages, completion_model = CHOSEN_COMP_MODEL)
    #     return response



    def run(self, query, lc_agent = None, history = None):
        
        print("history", history)
        answer = self.chat(query, lc_agent, history)
        print(answer)

        # self.update_history(query, answer)

        return answer