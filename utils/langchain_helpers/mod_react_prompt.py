from langchain.prompts import PromptTemplate, BasePromptTemplate


mod_react_prefix = """<|im_start|>Answer the following questions as best you can. You have access to the following tools:"""
mod_react_format_instructions_no_bing = """
You can try Cognitive Lookup first, then Redis Lookup, then Redis Search, then Cognitive Search, strictly in that order. After each time you use a tool, the assistant shall ponder carefully whether the observation has enough information to get a final answer or not BEFORE proceeding to the next tool. If you find an answer, you must stop searching. If you don't find an answer, you must continue searching with different action inputs until all tools are exhausted.

Use the following format strictly:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: [folder1/file1] the result of the action.\n [folder2/file2] second result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: [folder1/file1][folder2/file2] the final answer to the original input question

Observations have sources, you MUST include the source name in the final answer. If there are multiple sources, cite each one in their own square brackets. For example, use \"[folder3/info343][dir4/ref-76]\" and not \"[folder3/info343,dir4/ref-76]\". 
Never quote tool names as sources. YOU MUST STRICTLY USE THE COLLECTED EVIDENCE FROM THE OBSERVATIONS, FROM THE INITIAL CONTEXT OR FROM PREVIOUS CONVERSATION, DO NOT ANSWER FROM MEMORY.
You MUST NOT call the same action with the same action input more than once.

"""

mod_react_format_instructions_with_bing = """
You can try Cognitive Lookup first, then Redis Lookup, then Redis Search, then Cognitive Search, then Online Search strictly in that order. After each time you use a tool, the assistant shall ponder carefully whether the observation has enough information to get a final answer or not BEFORE proceeding to the next tool. If you find an answer, you must stop searching. If you don't find an answer, you must continue searching with different action inputs until all tools are exhausted.

Use the following format strictly:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: [folder1/file1] the result of the action.\n [folder2/file2] second result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: [folder1/file1][folder2/file2] the final answer to the original input question

Observations have sources, you MUST include the source name in the final answer. If there are multiple sources, cite each one in their own square brackets. For example, use \"[folder3/info343][dir4/ref-76]\" and not \"[folder3/info343,dir4/ref-76]\". 
Never quote tool names as sources. YOU MUST STRICTLY USE THE COLLECTED EVIDENCE FROM THE OBSERVATIONS, FROM THE INITIAL CONTEXT OR FROM PREVIOUS CONVERSATION, DO NOT ANSWER FROM MEMORY.
You MUST NOT call the same action with the same action input more than once.

"""
# NEVER CALL THE SAME TOOL AND ACTION WITH THE SAME ACTION INPUT MORE THAN ONCE.


mod_react_suffix = """Begin!
# <|im_end|>
# <|im_start|>user 
Question: {input}
<|im_end|>
# <|im_start|>assistant
Initial Context:{pre_context}
Conversation History: {history}
Thought:{agent_scratchpad}"""
