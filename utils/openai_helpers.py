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



openai.api_type = "azure"
openai.api_key = os.environ["OPENAI_API_KEY"]
openai.api_base = os.environ["OPENAI_RESOURCE_ENDPOINT"]
openai.api_version = "2022-12-01"




MAX_QUERY_TOKENS             = int(os.environ["MAX_QUERY_TOKENS"])
MAX_OUTPUT_TOKENS            = int(os.environ["MAX_OUTPUT_TOKENS"])

DAVINCI_003_MODEL_MAX_TOKENS = int(os.environ["DAVINCI_003_MODEL_MAX_TOKENS"])
ADA_002_MODEL_MAX_TOKENS     = int(os.environ["ADA_002_MODEL_MAX_TOKENS"])
DAVINCI_003_EMB_MAX_TOKENS   = int(os.environ['DAVINCI_003_EMB_MAX_TOKENS'])


GPT35_TURBO_COMPLETIONS_MODEL = os.environ['GPT35_TURBO_COMPLETIONS_MODEL']
GPT35_TURBO_COMPLETIONS_MAX_TOKENS = int(os.environ["GPT35_TURBO_COMPLETIONS_MAX_TOKENS"])

CHOSEN_EMB_MODEL        = os.environ['CHOSEN_EMB_MODEL']
CHOSEN_QUERY_EMB_MODEL  = os.environ['CHOSEN_QUERY_EMB_MODEL']
CHOSEN_COMP_MODEL       = os.environ['CHOSEN_COMP_MODEL']

RESTRICTIVE_PROMPT    = os.environ['RESTRICTIVE_PROMPT']


TEMPERATURE = 0




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

        while counter < 10:
            time.sleep(3)
            result = openai.Deployment.list()
            print(f"Found {len(result.data)} deployments")

            for deployment in result.data:
                #logging.info(f"Found deployment {deployment}")
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
    else:
        return ADA_002_MODEL_MAX_TOKENS




def get_encoder(embedding_model):
    if embedding_model == "text-search-davinci-doc-001":
        return tiktoken.get_encoding("p50k_base")
    elif embedding_model == "text-embedding-ada-002":
        return tiktoken.get_encoding("cl100k_base")
    elif embedding_model == "gpt-3.5-turbo": 
        return tiktoken.get_encoding("cl100k_base")
    else:
        return tiktoken.get_encoding("gpt2")



@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(20))
def get_openai_embedding(query, embedding_model):
    return openai.Embedding.create(input=query, engine=embedding_deployment_id)['data'][0]['embedding']



@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(20))
def openai_summarize(text, completion_model, max_output_tokens = MAX_OUTPUT_TOKENS, lang='en'):
    prompt = get_summ_prompt(text)
    return contact_openai(prompt, completion_model, max_output_tokens)



@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(20))
def contact_openai(prompt, completion_model, max_output_tokens):
    try:
        return openai.Completion.create(
                        prompt=prompt,
                        temperature=TEMPERATURE,
                        max_tokens=max_output_tokens,
                        model=completion_model,
                        deployment_id=completion_deployment_id
                    )["choices"][0]["text"].strip(" \n")
    except Exception as e:
        print(e)
        raise e




