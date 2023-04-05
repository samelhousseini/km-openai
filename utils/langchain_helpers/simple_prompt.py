import os
import logging
from datetime import datetime

RESTRICTIVE_PROMPT = os.environ['RESTRICTIVE_PROMPT']
GPT35_TURBO_COMPLETIONS_MODEL = os.environ['GPT35_TURBO_COMPLETIONS_MODEL']
CHOSEN_COMP_MODEL = os.environ['CHOSEN_COMP_MODEL']

GPT4_MODEL = "gpt-4"
GPT4_32K_MODEL = "gpt-4-32k"



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

strict_prompt = "If the facts below do not answer the question, say you don't know."

instruction_template = """The system is an AI assistant that helps people find information in the provided Context below. Only answer questions based on the facts listed below. {strict}
Facts have sources, you MUST include the source name in the answer at the beginning before any text. If there are multiple sources, cite each one in their own square brackets. For example, use \"[folder3/info343][http://wikipedia.com]\" and not \"[folder3/info343,http://wikipedia.com]\". The source name can either be in the format of "folder/file" or it can be an internet URL like "https://microsoft.com". You must follow the following format strictly for the final answer: 
Answer: [folder1/file1][http://wikipedia.com][http://microsoft.com] the answer based on the facts or information. 
The current time and date will be provided for the assistant in the Context. The assistant can use the current date and time to derive the day and date for any time-related questions, such as this afternoon, this evening, today, tomorrow, this weekend or next week.

The below are examples of final answers:

Question: "what is mentioned about the Lost City hotel?"
Answer: "[microsoft.com] The Lost City Hotel is a luxurious accommodation in Dubai with an onsite waterpark and aquarium."

Question: "what hotels are recommended in Las Vegas?"
Answer: "[folder/Las Vegas.pdf] Margie’s Travel offers the following hotels in Las Vegas: The Volcano Hotel, The Fountain Hotel, The Canal Hotel. To book your trip to Las Vegas, visit www.margiestravel.com."

Question: "who is Barack Obama?"
Answer: '[http://wikipedia.com] Barack Obama is the 44th President of the United States of America.'

Question: "who is Barack Obama?"
Answer: '[] Unfortunately, none of the sources I searched provided any specific information about Barack Obama.'

Question: "how much are the one day pass tickets for Ferrari world?"
Answer: "[] I'm sorry, I could not find the ticket prices for Ferrari World."

"""





def get_simple_prompt(context, query, history, pre_context):

    logging.info(f"{CHOSEN_COMP_MODEL}, {GPT35_TURBO_COMPLETIONS_MODEL}, {CHOSEN_COMP_MODEL == GPT35_TURBO_COMPLETIONS_MODEL}")
    print((f"Chosen Model: {CHOSEN_COMP_MODEL}, {GPT35_TURBO_COMPLETIONS_MODEL}, {CHOSEN_COMP_MODEL == GPT35_TURBO_COMPLETIONS_MODEL}"))
    todays_time = datetime.now().strftime('%A %B %d, %Y %H:%M:%S')

    instruction_strict = instruction_template.format(strict=strict_prompt)
    instruction_simple = instruction_template.format(strict="")

    if RESTRICTIVE_PROMPT == 'yes':
        instruction = instruction_strict
    else:
        instruction = instruction_simple

    if (CHOSEN_COMP_MODEL == GPT35_TURBO_COMPLETIONS_MODEL) or (CHOSEN_COMP_MODEL == GPT4_MODEL) or (CHOSEN_COMP_MODEL == GPT4_32K_MODEL):

        prompt = f"""
<|im_start|>system
{instruction}


<|im_end|>
<|im_start|>user


Initial Context: 
{pre_context}

Current Conversation: 
{history}

Context: 
[https://www.timeanddate.com] The current date and time are {datetime.now().strftime('%A %B %d, %Y %H:%M:%S')}. 

{context}

Question: {query}       
Answer:
<|im_end|>
<|im_start|>assistant
        """

    else:

        prompt =f"""{instruction}

Initial Context: 
{pre_context}

Current Conversation: 
{history}

Context: 
[https://www.timeanddate.com] The current date and time are {datetime.now().strftime('%A %B %d, %Y %H:%M:%S')}. 

{context}


Question: {query}       
Answer:

        """
    
    # logging.info(f"Using as prompt instruction: {instruction}")
    # print(f"Using as prompt instruction: {instruction}")

    return prompt