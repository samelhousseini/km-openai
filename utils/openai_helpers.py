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


EMBEDDING_MODEL = "text-embedding-ada-002"
EMB_QUERY_MODEL = "text-embedding-ada-002"
COMPLETIONS_MODEL = "text-davinci-003"


MAX_OUTPUT_TOKENS = 750
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




def get_prompt(context, query):

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



def get_encoder(embedding_model):
    if embedding_model == "text-search-davinci-doc-001":
        return tiktoken.get_encoding("p50k_base")
    elif embedding_model == "text-embedding-ada-002":
        return tiktoken.get_encoding("cl100k_base")
    else:
        return tiktoken.get_encoding("gpt2")



@retry(wait=wait_random_exponential(min=1, max=120), stop=stop_after_attempt(20))
def get_openai_embedding(query, embedding_model):
    #print(f"Generating Embeddings with {embedding_model}")
    deployment_id = check_model_deployment(embedding_model)
    logging.info(f"Get Embedding:: Found deployment {deployment_id}")
    return openai.Embedding.create(input=query, engine=deployment_id)['data'][0]['embedding']



@retry(wait=wait_random_exponential(min=1, max=120), stop=stop_after_attempt(20))
def openai_summarize(text, max_output_tokens = MAX_OUTPUT_TOKENS, lang='en'):
    prompt = get_summ_prompt(text)
    return contact_openai(prompt, max_output_tokens)



@retry(wait=wait_random_exponential(min=1, max=120), stop=stop_after_attempt(20))
def contact_openai(prompt, completion_model, max_output_tokens):
    print("contacting oai")
    
    deployment_id = check_model_deployment(completion_model)

    return openai.Completion.create(
                    prompt=prompt,
                    temperature=TEMPERATURE,
                    max_tokens=max_output_tokens,
                    model=completion_model,
                    deployment_id=deployment_id
                )["choices"][0]["text"].strip(" \n")



