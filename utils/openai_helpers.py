import openai
import tiktoken
import numpy as np
import os
import time
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)


from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate
)


from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)

from utils.env_vars import *


import openai
openai.api_version = OPENAI_API_VERSION



system_start_prompt = "<|im_start|>system "
user_start_prompt = "<|im_start|>user "
assistant_start_prompt = "<|im_start|>assistant "
end_prompt = "<|im_end|> "


system_start_prompt="""
<|im_end|>
<|im_start|>user
"""

append_tags = """
<|im_end|>
<|im_start|>assistant
"""



def check_model_deployment(oai_model):
    try:
        model_exists = False
        result = openai.Deployment.list()
        for deployment in result.data:
            if (deployment["model"] == oai_model):
                model_exists = True
                #logging.info(f"Found deployment {deployment}")
                return deployment["id"]
                

        if not model_exists: 
            openai.Deployment.create(model=oai_model, scale_settings={"scale_type":"standard"})
            time.sleep(30)
        assert model_exists, f"Model {oai_model} is not deployed, deploying now"
        
    except Exception as e:

        print(e)
        counter = 0
        deployed = False

        while counter < 2:
            time.sleep(2)
            result = openai.Deployment.list()
            print(f"Found {len(result.data)} deployments")

            for deployment in result.data:
                logging.info(f"OpenAI Deployment Exception --- Found deployment {deployment}")
                if (deployment["status"] == "succeeded") and (deployment["model"] == oai_model):
                    deployed = True
                    print(f"The right model {deployment['model']} was found")
                    return deployment["id"]
            
            if deployed: break
            
            counter += 1   

    return ""



completion_deployment_id = check_model_deployment(CHOSEN_COMP_MODEL)
embedding_deployment_id = check_model_deployment(CHOSEN_EMB_MODEL)



def experiment_prompt(context, query):

    prompt =f"""
    Context: {context}
    
    Question: {query}       
    
    
    Answer the question using the above Context only, and if the answer is not contained within the Context above, say "Sorry, I don't know":
    """
    


def get_summ_prompt(text):

    prompt =f"""
    Summarize the following text.

    Text:
    ###
    {text}
    ###

    Summary:
    """

    return prompt


def get_generation(model):
    if model == "text-davinci-003":
        return 3
    elif model == "gpt-35-turbo":
        return 3.5
    elif model == "gpt-4-32k":
        return 4
    elif model == "gpt-4":
        return 4
    else:
        assert False, f"Generation unknown for model {model}"



def convert_messages_to_roles(messages):
    roles = []
    for m in messages:
        if isinstance(m, HumanMessage):
            roles.append({'role':'user', 'content': m.content})
        elif isinstance(m, AIMessage):
            roles.append({'role':'assistant', 'content': m.content})
        elif isinstance(m, SystemMessage):
            roles.append({'role':'system', 'content': m.content})
        elif isinstance(m, Messages):
            roles.append({'role':'user', 'content': m.content})
        else:
            assert False, f"Unknown message type {type(m)}"

    return roles


def get_model_max_tokens(model):
    if model == "text-search-davinci-doc-001":
        return DAVINCI_003_EMB_MAX_TOKENS
    elif model == "text-search-davinci-query-001":
        return DAVINCI_003_EMB_MAX_TOKENS        
    elif model == "text-davinci-003":
        return DAVINCI_003_MODEL_MAX_TOKENS        
    elif model == "text-embedding-ada-002":
        return ADA_002_MODEL_MAX_TOKENS
    elif model == "gpt-35-turbo":
        return GPT35_TURBO_COMPLETIONS_MAX_TOKENS        
    elif model == "gpt-4-32k":
        return GPT4_32K_COMPLETIONS_MODEL_MAX_TOKENS     
    elif model == "gpt-4":
        return GPT4_COMPLETIONS_MODEL_MAX_TOKENS             
    else:
        return ADA_002_MODEL_MAX_TOKENS


def get_encoding_name(model):
    if model == "text-search-davinci-doc-001":
        return "p50k_base"
    elif model == "text-embedding-ada-002":
        return "cl100k_base"
    elif model == "gpt-35-turbo": 
        return "cl100k_base"
    elif model == "gpt-4-32k":
        return "cl100k_base"
    elif model == "gpt-4":
        return "cl100k_base"               
    elif model == "text-davinci-003":
        return "p50k_base"  
    else:
        return "gpt2"


def get_encoder(model):
    if model == "text-search-davinci-doc-001":
        return tiktoken.get_encoding("p50k_base")
    elif model == "text-embedding-ada-002":
        return tiktoken.get_encoding("cl100k_base")
    elif model == "gpt-35-turbo": 
        return tiktoken.get_encoding("cl100k_base")
    elif model == "gpt-4-32k":
        return tiktoken.get_encoding("cl100k_base")
    elif model == "gpt-4":
        return tiktoken.get_encoding("cl100k_base")                
    elif model == "text-davinci-003":
        return tiktoken.get_encoding("p50k_base")           
    else:
        return tiktoken.get_encoding("gpt2")



def get_model_dims(embedding_model):
    if embedding_model == "text-search-davinci-doc-001":
        return DAVINCI_003_EMBED_NUM_DIMS
    elif embedding_model == "text-embedding-ada-002":
        return ADA_002_EMBED_NUM_DIMS
    else:
        return ADA_002_EMBED_NUM_DIMS


def get_token_length(text, model = CHOSEN_COMP_MODEL):
    enc = get_encoder(model)
    return len(enc.encode(text))



@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(30))
def get_openai_embedding(query, embedding_model = CHOSEN_EMB_MODEL):
    return openai.Embedding.create(input=query, engine=embedding_deployment_id)['data'][0]['embedding']



@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(20))
def openai_summarize(text, completion_model, max_output_tokens = MAX_OUTPUT_TOKENS, lang='en'):
    prompt = get_summ_prompt(text)
    return contact_openai(prompt, completion_model, max_output_tokens)



@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(7))
def contact_openai(prompt, completion_model = CHOSEN_COMP_MODEL, max_output_tokens = MAX_OUTPUT_TOKENS, stream = False, verbose = False):
    if verbose: print("\n########################### Calling OAI Completion API - start call")

    gen = get_generation(completion_model)

    try:
        b = time.time()

        if (gen == 4) or (gen == 3.5):
            openai.api_version = "2023-03-15-preview"

            if not isinstance(prompt, list):
                prompt = [{'role':'user', 'content': prompt}]

            resp = openai.ChatCompletion.create(
                    messages=prompt,
                    temperature=TEMPERATURE,
                    max_tokens=max_output_tokens,
                    engine=completion_model,
                    stream = stream
                )
            a = time.time()
            if verbose: print(f"Using GPT-4 - Chat Completion - with stream {stream} - OpenAI response time: {a-b}")   
            if stream: return resp
            else: return resp["choices"][0]["message"]['content'].strip(" \n")

        else:
            openai.api_version = "2022-12-01"
            resp = openai.Completion.create(
                            prompt=prompt,
                            temperature=TEMPERATURE,
                            max_tokens=max_output_tokens,
                            model=completion_model,
                            deployment_id=completion_deployment_id,
                            stream = stream
                        )

            a = time.time()
            if verbose: print(f"Using GPT-3 - Chat Completion - with stream {stream} - OpenAI response time: {a-b}")                         
            if stream: return resp
            else: return resp["choices"][0]["text"].strip(" \n")

    except Exception as e:
        # logging.warning(f"Error in contact_openai: {e}")
        print(e)
        raise e



