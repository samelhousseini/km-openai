import openai
import tiktoken
import numpy as np
import os
import time
import logging
import re

from langchain.llms.openai import AzureOpenAI
from langchain.agents import load_tools
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI
from langchain.prompts.prompt import PromptTemplate
from langchain.evaluation.qa import QAEvalChain
from langchain import LLMMathChain
from langchain.agents import Tool, AgentExecutor
from langchain.prompts import PromptTemplate, BasePromptTemplate
from langchain.agents.mrkl.base import ZeroShotAgent
from typing import Any, Callable, List, NamedTuple, Optional, Sequence, Tuple
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from langchain.tools.base import BaseTool
from langchain.agents.agent import Agent, AgentExecutor
from langchain.agents.react.base import ReActDocstoreAgent
from langchain.schema import AgentAction, AgentFinish

from utils.langchain_helpers.mod_wiki_prompt import mod_wiki_prompt
from utils.langchain_helpers.mod_react_prompt import mod_react_prefix, mod_react_format_instructions_no_bing, mod_react_format_instructions_with_bing, mod_react_suffix

from utils import openai_helpers


DAVINCI_003_MODEL_MAX_TOKENS = int(os.environ["DAVINCI_003_MODEL_MAX_TOKENS"])
ADA_002_MODEL_MAX_TOKENS     = int(os.environ["ADA_002_MODEL_MAX_TOKENS"])
DAVINCI_003_EMB_MAX_TOKENS   = int(os.environ['DAVINCI_003_EMB_MAX_TOKENS'])
GPT35_TURBO_COMPLETIONS_MODEL = os.environ['GPT35_TURBO_COMPLETIONS_MODEL']


CHOSEN_EMB_MODEL        = os.environ['CHOSEN_EMB_MODEL']
CHOSEN_QUERY_EMB_MODEL  = os.environ['CHOSEN_QUERY_EMB_MODEL']

NUM_TOP_MATCHES = int(os.environ['NUM_TOP_MATCHES'])
CHOSEN_COMP_MODEL = os.environ.get("CHOSEN_COMP_MODEL")
GPT35_TURBO_COMPLETIONS_MAX_TOKENS = int(os.environ.get("GPT35_TURBO_COMPLETIONS_MAX_TOKENS"))
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS"))
MAX_QUERY_TOKENS = int(os.environ.get("MAX_QUERY_TOKENS"))
MAX_HISTORY_TOKENS = int(os.environ.get("MAX_HISTORY_TOKENS"))
MAX_SEARCH_TOKENS  = int(os.environ.get("MAX_SEARCH_TOKENS"))
PRE_CONTEXT = int(os.environ.get("PRE_CONTEXT"))

USE_BING = os.environ.get("USE_BING")



class GPT35TurboAzureOpenAI(AzureOpenAI):
    stop: List[str] = None
    @property
    def _invocation_params(self):
        params = super()._invocation_params
        params.pop('logprobs', None)
        params.pop('best_of', None)
        params.pop('echo', None)
        return params



class ModAgent(Agent):

    history_length: int = 0
    query_length: int = 0
    pre_context_length  : int = 0



    def _get_next_action(self, full_inputs: Dict[str, str]) -> AgentAction:
        # print("@@@@@ full_inputs", full_inputs)
        full_output = self.llm_chain.predict(**full_inputs)
        # print("@@@@@ full_output", full_output)
        parsed_output = self._extract_tool_and_input(full_output)

        # if parsed_output is None:                
        #     # print("@@@@@ parsed_output", parsed_output)
        #     parsed_output = ['Finish', full_output]

        while parsed_output is None:
            full_output = self._fix_text(full_output)
            full_inputs["agent_scratchpad"] += full_output
            # print("LOOOOPING", full_output)
            output = self.llm_chain.predict(**full_inputs)
            full_output += output
            parsed_output = self._extract_tool_and_input(full_output)

            if parsed_output is None:
                parsed_output = ['Finish', full_output]

        return AgentAction(
            tool=parsed_output[0], tool_input=parsed_output[1], log=full_output
        )


    def _construct_scratchpad(
        self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> str:
        """Construct the scratchpad that lets the agent continue its thought process."""
        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
        thoughts = ""

        # print('-------------------------------------.query_length', self.query_length)
        # print('-------------------------------------.pre_context_length', self.pre_context_length)
        # print('-------------------------------------.history_length', self.history_length)

        pr = self.create_prompt([]).format(history='', input='', agent_scratchpad='', pre_context='')
        empty_prompt_length = len(completion_enc.encode(pr))


        len_steps = len(intermediate_steps)
        th_tokens = 0
        len_obs = []
        obs_str = ""
        
        max_comp_model_tokens = openai_helpers.get_model_max_tokens(CHOSEN_COMP_MODEL)

        if len_steps > 0:
            th_str = ""
            for action, observation in intermediate_steps:
                th_str += action.log
                th_str += f"\n{self.observation_prefix}\n{self.llm_prefix}"
            
            th_tokens = len(completion_enc.encode(th_str))
            
            allowance = max_comp_model_tokens - th_tokens - empty_prompt_length - MAX_OUTPUT_TOKENS - self.history_length - self.query_length - self.pre_context_length
            if allowance < 0: allowance = 0
            allowance_per_step = allowance // len_steps

            for action, observation in intermediate_steps:
                obs_str += observation
                len_obs.append(len(completion_enc.encode(observation)))

            obs_tokens = sum(len_obs)

            avail_allowance = 0
            

            if obs_tokens > allowance:
                for i in range(len(len_obs)):
                    if len_obs[i] < allowance_per_step:
                        avail_allowance += allowance_per_step - len_obs[i]
                
                for i in reversed(range(len(len_obs))):    
                    if len_obs[i] > allowance_per_step:                                    
                        avail_allowance = avail_allowance // 2
                        len_obs[i] = allowance_per_step + avail_allowance 

        else:
            allowance = max_comp_model_tokens - empty_prompt_length - MAX_OUTPUT_TOKENS - self.query_length - self.history_length - self.pre_context_length
            if allowance < 0: allowance = 0
            len_obs.append(allowance)

        # print(max_comp_model_tokens, th_tokens, empty_prompt_length, MAX_OUTPUT_TOKENS, self.history_length, self.query_length, self.pre_context_length)

        i = 0
        for action, observation in intermediate_steps:
            thoughts += action.log
            trunc_comp = completion_enc.decode(completion_enc.encode(observation)[:len_obs[i]])
            thoughts += f"\n{self.observation_prefix}{trunc_comp}\n{self.llm_prefix}" 
            i += 1

        # print("\nNUM STEPS:",str(len_steps), "TH_TOKENS", th_tokens, "ALLOWANCE", allowance, "USED", len(completion_enc.encode(thoughts)), 'LEN_OBS', len_obs, "\n")            
        return thoughts








class ReAct(ReActDocstoreAgent, ModAgent):
    @classmethod
    def create_prompt(cls, tools: List[Tool]) -> BasePromptTemplate:
        return mod_wiki_prompt


    def _extract_tool_and_input(self, text: str) -> Optional[Tuple[str, str]]:
        action_prefix = f"Action {self.i}: "
        # print("action_prefix", action_prefix, "\n")

        if not text.split("\n")[-1].startswith(action_prefix): 
            return None

        self.i += 1
        action_block = text.split("\n")[-1]

        action_str = action_block[len(action_prefix) :]
        # Parse out the action and the directive.
        re_matches = re.search(r"(.*?)\[(.*?)\]", action_str)

        # print('re_matches', re_matches.group(1), re_matches.group(2), '\n')

        if re_matches is None:
            raise ValueError(f"Could not parse action directive: {action_str}")
        return re_matches.group(1), re_matches.group(2)





class ZSReAct(ZeroShotAgent, ModAgent):

    @classmethod
    def create_prompt(
        cls,
        tools: Sequence[BaseTool],
        prefix: str = mod_react_prefix,
        suffix: str = mod_react_suffix,
        format_instructions: str = mod_react_format_instructions_no_bing,
        input_variables: Optional[List[str]] = None,
        ) -> PromptTemplate:
        
        tool_strings = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
        tool_names = ", ".join([tool.name for tool in tools])

        if USE_BING == 'yes':
            format_instructions = mod_react_format_instructions_with_bing.format(tool_names=tool_names)
        else:
            format_instructions = mod_react_format_instructions_no_bing.format(tool_names=tool_names)

        template = "\n\n".join([mod_react_prefix, tool_strings, format_instructions, mod_react_suffix])

        if input_variables is None:
            input_variables = ["input", "agent_scratchpad", "history", "pre_context"]
        return PromptTemplate(template=template, input_variables=input_variables)        




    def _extract_tool_and_input(self, text: str) -> Optional[Tuple[str, str]]:
        try:
            return self.get_action_and_input_mod(text)
        except Exception as e:
            print("GOING TO FINAL ANSWER. EXCEPTION:", e, "\n")
            return "Final Answer", text.replace("Action: None", '').replace("Could not parse", '')



    def get_action_and_input_mod(self, llm_output: str) -> Tuple[str, str]:
        """Parse out the action and input from the LLM output.

        Note: if you're specifying a custom prompt for the ZeroShotAgent,
        you will need to ensure that it meets the following Regex requirements.
        The string starting with "Action:" and the following string starting
        with "Action Input:" should be separated by a newline.
        """
        FINAL_ANSWER_ACTION = "Final Answer:"
        
        if FINAL_ANSWER_ACTION in llm_output:
            return "Final Answer", llm_output.split(FINAL_ANSWER_ACTION)[-1].strip()
        regex = r"Action:[\n\r\s]+(.*?)[\n]*Action Input:[\n\r\s](.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            regex = r"Action:[\n\r\s]+(.*?)[\n]*[\n\r\s](.*)"
            match = re.search(regex, s, re.DOTALL)
            print("MATCH", match)
            # .replace("Action: None needed", '').replace("Action: None", "").replace("Action: N/A", "").replace("Action:", "")
            return "Final Answer", llm_output.replace(match, '').replace('<|im_end|>', '').replace('\n\n', '') 
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)
        return action, action_input.strip(" ").strip('"')


