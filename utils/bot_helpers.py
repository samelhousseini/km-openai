import os
import pickle
import numpy as np
import tiktoken
import json
import logging

from utils import language
from utils import storage
from utils import redis_helpers
from utils import openai_helpers
from utils import cosmos_helpers

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

        
redis_conn = redis_helpers.get_new_conn() 



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


## Original Prompt - too strict for OpenAI
## Answer the question using the above Context only, and if the answer is not contained within the Context above, say "Sorry, the query did not find a good match. Please rephrase your question":


def get_prompt(context, query, completion_model = None):

    logging.info(f"{completion_model}, {GPT35_TURBO_COMPLETIONS_MODEL}, {completion_model == GPT35_TURBO_COMPLETIONS_MODEL}")

    if completion_model == GPT35_TURBO_COMPLETIONS_MODEL:


        if RESTRICTIVE_PROMPT == 'yes':
            instruction = "The system is an AI assistant that helps people find information in the provided context below. Only answer questions based on the facts listed below. If the facts below don't answer the question, say you don't know. "
        else:
            instruction = "The system is an AI assistant that helps people find information in the provided context below. Only answer questions based on the facts listed below."


        prompt = f"""
        <|im_start|>system
        {instruction}
        {context}
        <|im_end|>
        <|im_start|>user
        {query}       
        <|im_end|>
        <|im_start|>assistant

        """

    else:

        if RESTRICTIVE_PROMPT == 'yes':
            instruction = "Answer the question using the above Context only, and if the answer is not contained within the Context above, say 'Sorry, the query did not find a good match. Please rephrase your question':"
        else:
            instruction = "Answer the question using the above Context:"


        prompt =f"""
        Context: {context}
        
        Question: {query}       
        
        {instruction}
        """
    
    logging.info(f"Using as prompt instruction: {instruction}")
    print(f"Using as prompt instruction: {instruction}")

    return prompt







def openai_interrogate_text(query, completion_model, embedding_model, prev_prompt=None, topK=5, verbose=False):
    
    print(f"Interrogating Text with embedding mode {embedding_model} and completion model {completion_model}")
    logging.info(f"Interrogating Text with embedding mode {embedding_model} and completion model {completion_model}")

    results = None

    query = query.lower()

    completion_enc = openai_helpers.get_encoder(completion_model)
    embedding_enc = openai_helpers.get_encoder(embedding_model)

    lang = language.detect_content_language(query)
    if lang != 'en': query = language.translate(query, lang, 'en')

    max_comp_model_tokens = get_model_max_tokens(completion_model)

    if (not prev_prompt is None) and (prev_prompt != '') and (completion_model == GPT35_TURBO_COMPLETIONS_MODEL):

        end_of_prev_prompt_tags="""
        <|im_end|>
        <|im_start|>user
        """

        append_tags = """
        <|im_end|>
        <|im_start|>assistant
        """
        prev_prompt_length = len(completion_enc.encode(prev_prompt))
        query_length       = len(completion_enc.encode(query))
        append_tags_len    = len(completion_enc.encode(append_tags))
        end_of_prev_prompt_tags_len = len(completion_enc.encode(end_of_prev_prompt_tags))
        max_context_len = max_comp_model_tokens - query_length - MAX_OUTPUT_TOKENS - append_tags_len - 1


        if prev_prompt_length > (max_context_len - end_of_prev_prompt_tags_len):
            prev_prompt = completion_enc.decode(completion_enc.encode(prev_prompt)[:max_context_len - end_of_prev_prompt_tags_len])
            prev_prompt += end_of_prev_prompt_tags 
            print(prev_prompt)

        prompt = f"""
        {prev_prompt}
        {query}
        {append_tags}
        """

    else:

        max_emb_model_tokens = get_model_max_tokens(embedding_model)
        max_emb_model_tokens = min(max_emb_model_tokens, MAX_QUERY_TOKENS)

        query = embedding_enc.decode(embedding_enc.encode(query)[:max_emb_model_tokens])
        query_embedding = openai_helpers.get_openai_embedding(query, embedding_model)
        
        results = redis_helpers.redis_query_embedding_index(redis_conn, query_embedding, -1, topK=topK)

        if len(results) == 0:
            logging.warning("No embeddings found in Redis, attempting to load embeddings from Cosmos")
            cosmos_helpers.cosmos_restore_embeddings()
            results = redis_helpers.redis_query_embedding_index(redis_conn, query_embedding, -1, topK=topK)
            
        if len(results) == 0:        
            logging.warning("No embeddings found in Redis or Cosmos")
            return "Sorry, no embeddings are loaded in Redis or Cosmos"

        first_score = float(results[0]['score'])    
        context = '\n\n\n'.join([t['text_en'] for t in results])

        empty_prompt_length = len(completion_enc.encode(get_prompt('', '', CHOSEN_COMP_MODEL)))
        context_length      = len(completion_enc.encode(context))
        orig_query_length   = len(completion_enc.encode(query))
        query_length        = len(completion_enc.encode(query))
    
        max_context_len = max_comp_model_tokens - query_length - MAX_OUTPUT_TOKENS - empty_prompt_length - 1
        
        context = completion_enc.decode(completion_enc.encode(context)[:max_context_len])
        prompt = get_prompt(context, query, CHOSEN_COMP_MODEL)





    final_answer = openai_helpers.contact_openai(prompt, completion_model, MAX_OUTPUT_TOKENS)
    
    if results is None:
        context = ''
    else:
        context = results[0]['text_en']

    if lang != 'en': 
        final_answer = language.translate(final_answer, 'en', lang)
        
        if context != '':
            context = language.translate(context, 'en', lang)    


    try:
        doc_url = results[0]['doc_url']
    except:
        doc_url = "No URL found"
    
    if verbose:
        print("##############################################################################")
        [print("Scores", t['score'], t['id']) for t in results]
        print("original query length", orig_query_length)
        print("query length", query_length)
        print("context length", context_length)
        print("empty prompt length", empty_prompt_length)
        print("max context tokens", max_context_len)
        print("full prompt length", len(completion_enc.encode(prompt)))
        print("Prompt", prompt)
        print("##############################################################################")


    while final_answer.startswith("Answer:"):
        final_answer = final_answer[7:].strip()

    final_answer = final_answer.replace('<|im_end|>', '')

    ret_dict  = {
        "link": doc_url,
        "answer": final_answer,
        "context": context
    }

    if completion_model == GPT35_TURBO_COMPLETIONS_MODEL:
        ret_dict['prompt'] = f"""
        {prompt}
        {final_answer}
        <|im_end|>
        <|im_start|>user
        """

    
    return json.dumps(ret_dict, indent=4) 