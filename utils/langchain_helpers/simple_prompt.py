import os
import logging


RESTRICTIVE_PROMPT = os.environ['RESTRICTIVE_PROMPT']
GPT35_TURBO_COMPLETIONS_MODEL = os.environ['GPT35_TURBO_COMPLETIONS_MODEL']
CHOSEN_COMP_MODEL = os.environ['CHOSEN_COMP_MODEL']




## Original Prompt - too strict for OpenAI
## Answer the question using the above Context only, and if the answer is not contained within the Context above, say "Sorry, the query did not find a good match. Please rephrase your question":

end_of_prev_prompt_tags="""
<|im_end|>
<|im_start|>user
"""

append_tags = """
<|im_end|>
<|im_start|>assistant
"""


def get_simple_prompt(context, query, history, pre_context):

    logging.info(f"{CHOSEN_COMP_MODEL}, {GPT35_TURBO_COMPLETIONS_MODEL}, {CHOSEN_COMP_MODEL == GPT35_TURBO_COMPLETIONS_MODEL}")

    if CHOSEN_COMP_MODEL == GPT35_TURBO_COMPLETIONS_MODEL:


        if RESTRICTIVE_PROMPT == 'yes':
            instruction = "The system is an AI assistant that helps people find information in the provided Context below. Only answer questions based on the facts listed below. If the Initial Context and Context below doesn't answer the question, say you don't know. "
        else:
            instruction = "The system is an AI assistant that helps people find information in the provided context below. Only answer questions based on the facts listed below."

        prompt = f"""
<|im_start|>system
{instruction}

Initial Context:
####
{pre_context}
####

Context: 
####
{context}
####

<|im_end|>
<|im_start|>user
Current Conversation: 
####
{history}
####

Question: {query}       
<|im_end|>
<|im_start|>assistant
        """

    else:

        if RESTRICTIVE_PROMPT == 'yes':
            instruction = "Answer the question using the above Initial Context and Context only, and if the answer is not contained within the Initial Context and Context above, say 'Sorry, the query did not find a good match. Please rephrase your question':"
        else:
            instruction = "Answer the question using the above Initial Context and Context:"


        prompt =f"""
Initial Context:
####
{pre_context}
####

Context: 
####
{context}
####

Current Conversation: 
####
{history}
####

Question: {query}       

{instruction}
        """
    
    logging.info(f"Using as prompt instruction: {instruction}")
    print(f"Using as prompt instruction: {instruction}")

    return prompt