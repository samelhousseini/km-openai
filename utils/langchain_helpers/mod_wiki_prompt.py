from langchain.prompts import PromptTemplate, BasePromptTemplate


EXAMPLES = [
#     """Question: What is the elevation range for the area that the eastern sector of the Colorado orogeny extends into?
# Thought 1: I need to search Colorado orogeny, find the area that the eastern sector of the Colorado orogeny extends into, then find the elevation range of the area.
# Action 1: Search[Colorado orogeny]
# Observation 1: [info1.pdf] The Colorado orogeny was an episode of mountain building (an orogeny) in Colorado and surrounding areas.
# Thought 2: It does not mention the eastern sector. So I need to look up eastern sector.
# Action 2: Lookup[eastern sector]
# Observation 2: [info2.txt] (Result 1 / 1) The eastern sector extends into the High Plains and is called the Central Plains orogeny.
# Thought 3: The eastern sector of Colorado orogeny extends into the High Plains. So I need to search High Plains and find its elevation range.
# Action 3: Search[High Plains]
# Observation 3: [some_file.pdf] High Plains refers to one of two distinct land regions
# Thought 4: I need to instead search High Plains (United States).
# Action 4: Search[High Plains (United States)]
# Observation 4: [filea.pdf] The High Plains are a subregion of the Great Plains. [another-ref.docx] From east to west, the High Plains rise in elevation from around 1,800 to 7,000 ft (550 to 2,130m).
# Thought 5: High Plains rise in elevation from around 1,800 to 7,000 ft, so the answer is 1,800 to 7,000 ft.
# Action 5: Finish[1,800 to 7,000 ft [filea.pdf]]\n\n""",
#     """Question: Musician and satirist Allie Goertz wrote a song about the "The Simpsons" character Milhouse, who Matt Groening named after who?
# Thought 1: The question simplifies to "The Simpsons" character Milhouse is named after who. I only need to search Milhouse and find who it is named after.
# Action 1: Search[Milhouse]
# Observation 1: [info7.pdf] Milhouse Mussolini Van Houten is a recurring character in the Fox animated television series The Simpsons voiced by Pamela Hayden and created by Matt Groening.
# Thought 2: The paragraph does not tell who Milhouse is named after, maybe I can look up "named after".
# Action 2: Lookup[named after]
# Observation 2: [historyref2.txt] (Result 1 / 1) Milhouse was named after U.S. president Richard Nixon, whose middle name was Milhous.
# Thought 3: Milhouse was named after U.S. president Richard Nixon, so the answer is Richard Nixon.
# Action 3: Finish[(historyref2.txt) Richard Nixon\n\n]""",
    """Question: Which documentary is about Finnish rock groups, Adam Clayton Powell or The Saimaa Gesture?
Thought 1: I need to search Adam Clayton Powell and The Saimaa Gesture, and find which documentary is about Finnish rock groups.
Action 1: Search[Adam Clayton Powell]
Observation 1: [info9.pdf] Could not find [Adam Clayton Powell]. Similar: ['Adam Clayton Powell III', 'Seventh Avenue (Manhattan)', 'Adam Clayton Powell Jr. State Office
Building', 'Isabel Washington Powell', 'Adam Powell', vAdam Clayton Powell (film)', 'Giancarlo Esposito'].
Thought 2: To find the documentary, I can search Adam Clayton Powell (film).
Action 2: Search[Adam Clayton Powell (film)]
Observation 2: [data123.txt] Adam Clayton Powell is a 1989 American documentary film directed by Richard Kilberg. The film is about the rise and fall of influential African-American politician Adam Clayton Powell Jr.[3][4] It was later aired as part of the PBS series The American Experience.
Thought 3: Adam Clayton Powell (film) is a documentary about an African-American
politician, not Finnish rock groups. So the documentary about Finnish rock groups must instead be The Saimaa Gesture.
Action 3: Finish[[data123.txt] The Saimaa Gesture]""",
    """Question: What profession does Nicholas Ray and Elia Kazan have in common?
Thought 1: I need to search Nicholas Ray and Elia Kazan, find their professions, then find the profession they have in common.
Action 1: Search[Nicholas Ray]
Observation 1: [files-987.png] Nicholas Ray (born Raymond Nicholas Kienzle Jr., August 7, 1911 - June 16, 1979) was an American film director, screenwriter, and actor best known for the 1955 film Rebel Without a Cause.
Thought 2: Professions of Nicholas Ray are director, screenwriter, and actor. I need to search Elia Kazan next and find his professions.
Action 2: Search[Elia Kazan]
Observation 2: [files-654.txt] Elia Kazan was an American film and theatre director, producer, screenwriter and actor.
Thought 3: Professions of Elia Kazan are director, producer, screenwriter, and actor. So profession Nicholas Ray and Elia Kazan have in common is director, screenwriter, and actor.
Action 3: Finish[[files-987.png](files-654.txt] director, screenwriter, actor]""",
    """Question: Which magazine was started first Arthur's Magazine or First for Women?
Thought 1: I need to search Arthur's Magazine and First for Women, and find which was started first.
Action 1: Search[Arthur's Magazine]
Observation 1: [magazines-1850.pdf] Arthur's Magazine (1844-1846) was an American literary periodical published in Philadelphia in the 19th century.
Thought 2: Arthur's Magazine was started in 1844. I need to search First for Women next.
Action 2: Search[First for Women]
Observation 2: [magazines-1900.pdf] First for Women is a woman's magazine published by Bauer Media Group in the USA.[1] The magazine was started in 1989.
Thought 3: First for Women was started in 1989. 1844 (Arthur's Magazine) < 1989 (First for Women), so Arthur's Magazine was started first.
Action 3: Finish[[magazines-1850.pdf)(magazines-1900.pdf) Arthur's Magazine]""",
    """Question: Were Pavel Urysohn and Leonid Levin known for the same type of work?
Thought 1: I need to search Pavel Urysohn and Leonid Levin, find their types of work, then find if they are the same.
Action 1: Search[Pavel Urysohn]
Observation 1: [info4444.pdf] Pavel Samuilovich Urysohn (February 3, 1898 - August 17, 1924) was a Soviet mathematician who is best known for his contributions in dimension theory.
Thought 2: Pavel Urysohn is a mathematician. I need to search Leonid Levin next and find its type of work.
Action 2: Search[Leonid Levin]
Observation 2: [datapoints_aaa.txt] Leonid Anatolievich Levin is a Soviet-American mathematician and computer scientist.
Thought 3: Leonid Levin is a mathematician and computer scientist. So Pavel Urysohn and Leonid Levin have the same type of work.
Action 3: Finish[[info4444.pdf] yes ]""",
]


SUFFIX = """

Initial Context:{pre_context}

Current Conversation: {history}

Question: {input}

<|im_end|>
<|im_start|>assistant

Begin:

{agent_scratchpad}
"""



PREFIX = """<|im_start|>system
The following is a friendly conversation between a human and an AI assistant. The AI assistant is talkative and provides lots of specific details from its context. You are an intelligent assistant helping our employees with their knowledge base questions. Answer questions as shown in the following examples, by splitting the question into individual search or lookup actions to find facts until you can answer the question. 
Observations are prefixed by their source name in square brackets, source names MUST be included with the actions in the answers.
All questions must be answered from the results from search or look up actions, only facts resulting from those can be used in an answer.
Answer questions as truthfully as possible, and ONLY answer the questions using the information from observations, do not speculate or your own knowledge.
If the question is not clear or further clarifications are needed, the AI assistant MUST use the search or lookup actions to get the context and information. The AI assistant MUST use one of the tools AT LEAST ONCE. 
At each Observation, the assistant shall ponder carefully whether it has the final answer or not. If the assistant does, then the assistant can stop searching and provide the final answer. If the assistant does not, then the assistant must continue searching until all search sources are exhausted.
Do NOT answer based on your knowledge of Wikipedia.
For example, if the question is \"What color is the sky?\" and one of the information sources says \"info123: the sky is blue whenever it's not cloudy\", then answer with \"The sky is blue [info123]\" 
It's important to strictly follow the format where the name of the source is in brackets at the end of the sentence, and only up to the prefix before the colon [\":\"]. 
If there are multiple sources, cite each one in their own square brackets. For example, use \"[info343][ref-76]\" and not \"[info343,ref-76]\". 
Never quote tool names as sources.

<|im_end|>
<|im_start|>user 

"""



mod_wiki_prompt = PromptTemplate.from_examples(
    EXAMPLES, SUFFIX, ["input", "agent_scratchpad", "history", "pre_context"], '\n', PREFIX
)












# PREFIX = """<|im_start|>system
# The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. Observations are prefixed by their reference name in square brackets, reference names MUST be included with the actions in the answers.
# Answer the following questions as best you can. You have access to the following tools:
# Search: useful for when you need to answer questions from the local knowledge store, and to get more context
# Lookup: useful for when you need to lookup terms from the local knowledge store, and to get more context
# The assistant MUST use the following search sources to deduce an asnwer: Search or Lookup. All questions MUST be answered from the results from these search sources, only facts resulting from those sources can be used in an answer. If any piece of information is missing, the assistant must be persistent in finding it from search sources until all tools are exhausted. 
# If a source provides enough evidence for an answer, then the assistant can deduce a final answer without trying other sources.
# If the question is not related to the previous conversation, then the assistant must use Search or Lookup to answer the question and ignore the previous conversation. 
# If this question is too broad and unclear, or if the assistant needs more context to understand the question, then the assistant can use Search or Lookup to find a more specific question to use with the tools at its disposal.
# At each Observation, the assistant shall ponder carefully whether it has the final answer or not. If the assistant does, then the assistant can stop searching and provide the final answer. If the assistant does not, then the assistant must continue searching until all search sources are exhausted.
# If the answer can be fully answered from the previous conversation, then the answer MUST be elaborated and repeated again and sent back to the user as a Final Asnwer.

# """

# PREFIX = """<|im_start|>system
# The following is a friendly conversation between a human and an AI assistant. The AI assistant is talkative and provides lots of specific details from its context. 
# Answer questions as shown in the following examples, by splitting the question into individual search or lookup actions to find facts until you can answer the question. 
# Observations are prefixed by their source name in square brackets, source names MUST be included with the actions in the answers.
# All questions must be answered from the results from search or look up actions, only facts resulting from those can be used in an answer. 
# Answer questions as truthfully as possible, and ONLY answer the questions using the information from observations, do not speculate or answer based on the assistant's own knowledge.
# If the question is not clear or further clarifications are needed, the AI assistant MUST use the search or lookup actions to get the context and information. The AI assistant MUST use one of the tools AT LEAST ONCE. Do NOT answer based on Wikipedia.
# Answer the question using the provided Observations only, and if the answer is not contained within the Observations, say "Sorry, the query did not find a good match. Please rephrase your question":
# """

# PREFIX = \
# """You are an intelligent assistant helping our employees with their knowledge base questions. 
# Answer the question using only the data provided in the information sources below. 
# Each source has a name followed by colon and the actual data, quote the source name for each piece of data you use in the response. 
# For example, if the question is \"What color is the sky?\" and one of the information sources says \"info123: the sky is blue whenever it's not cloudy\", then answer with \"The sky is blue (info123)\" 
# It's important to strictly follow the format where the name of the source is in parenthesis at the end of the sentence, and only up to the prefix before the colon (\":\"). 
# If there are multiple sources, cite each one in their own square brackets. For example, use \"(info343)(ref-76)\" and not \"(info343,ref-76)\". 
# Never quote tool names as sources.
# Answer questions as truthfully as possible, and ONLY answer the questions using the information from observations, do not speculate or answer based on the assistant's own knowledge.
# If the question is not clear or further clarifications are needed, the AI assistant MUST use the search or lookup actions to get the context and information. The AI assistant MUST use one of the tools AT LEAST ONCE. 
# If you cannot answer using the sources below, say that you don't know. 
# \n\nYou can access to the following tools:"""