import openai
import tiktoken
import numpy as np
import os
import time
import logging
import re

from datetime import date


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
from langchain.utilities import BingSearchAPIWrapper
from utils.langchain_helpers.mod_wiki_prompt import mod_wiki_prompt
from langchain.agents.conversational_chat.base import ConversationalChatAgent, AgentOutputParser

import utils.langchain_helpers.mod_react_prompt
import requests
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
BING_SUBSCRIPTION_KEY = os.environ.get("BING_SUBSCRIPTION_KEY")
BING_SEARCH_URL = os.environ.get("BING_SEARCH_URL")
LIST_OF_COMMA_SEPARATED_URLS = os.environ.get("LIST_OF_COMMA_SEPARATED_URLS")



class ModBingSearchAPIWrapper(BingSearchAPIWrapper):
    
    sites : str = None

    def _bing_search_results(self, search_term: str, count: int) -> List[dict]:
        
        headers = {"Ocp-Apim-Subscription-Key": self.bing_subscription_key}
        params = {
            "q": search_term,
            "count": count,
            "textDecorations": False,
            "textFormat": "Raw",
            "safeSearch": "Strict",
        }

        response = requests.get(
            self.bing_search_url, headers=headers, params=params  # type: ignore
        )
        response.raise_for_status()
        search_results = response.json()

        return search_results["webPages"]["value"]


    def run(self, query: str) -> str:
        """Run query through BingSearch and parse result."""

        if self.sites is None:
            self.sites = ""
            arr = LIST_OF_COMMA_SEPARATED_URLS.split(",")
            if len(arr) > 0:
                sites_v = ["site:"+site.strip() for site in arr]
                sites_v = " OR ".join(sites_v)
                sites_v = f"({sites_v})"
                self.sites = sites_v

            # print("Sites", self.sites)

        snippets = []
        try:
            results = self._bing_search_results(f"{self.sites} {query}", count=self.k)
        except Exception as e:
            print("Error in bing search", e)
            return snippets

        if len(results) == 0:
            return "No good Bing Search Result was found"
        for result in results:
            snippets.append('['+result["url"] + '] ' + result["snippet"])
        
        return snippets





class GPT35TurboAzureOpenAI(AzureOpenAI):
    stop: List[str] = None
    @property
    def _invocation_params(self):
        params = super()._invocation_params
        params.pop('logprobs', None)
        params.pop('best_of', None)
        params.pop('echo', None)
        # print(params)
        return params



class ModAgent(Agent):

    history_length: int = 0
    query_length: int = 0
    pre_context_length  : int = 0

    def _get_next_action(self, full_inputs: Dict[str, str]) -> AgentAction:
        full_output = self.llm_chain.predict(**full_inputs)
        # print("@@@@@ full_output", full_output)
        full_output = full_output.replace('<|im_end|>', '')
        parsed_output = self._extract_tool_and_input(full_output)

        while parsed_output is None:
            full_output = self._fix_text(full_output)
            full_inputs["agent_scratchpad"] += full_output
            print("LOOOOPING", full_output)
            output = self.llm_chain.predict(**full_inputs)
            full_output += output
            parsed_output = self._extract_tool_and_input(full_output)

            if parsed_output is None:
                parsed_output = ['Finish', full_output]

        return AgentAction(
            tool=parsed_output[0], tool_input=parsed_output[1], log=full_output
        )


    def _construct_scratchpad_token_analysis(
        self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> str:
        """Construct the scratchpad that lets the agent continue its thought process."""
        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
        thoughts = ""

        prt = self.create_prompt([])
        if prt.input_variables == ["input", "history", "agent_scratchpad"]:
            pr = prt.format(input='', history='', agent_scratchpad='')
        else:
            pr = prt.format(input='', chat_history=[], agent_scratchpad=[])
        # print(pr.input_variables)
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
                th_str += f"\n{self.observation_prefix}\n\n\n\n{self.llm_prefix}"
            
            th_tokens = len(completion_enc.encode(th_str))
            
            allowance = max_comp_model_tokens - th_tokens - empty_prompt_length - MAX_OUTPUT_TOKENS - self.history_length - self.query_length - self.pre_context_length - len_steps * 30
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

        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log + f"\n{self.observation_prefix}{observation}\n{self.llm_prefix}" 

        drop_first = False
        if len(completion_enc.encode(thoughts)) > 0.8 * allowance:
            drop_first = True

        return len_obs, len_steps, th_tokens, allowance


    def _construct_scratchpad(
        self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> str:
        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
        
        len_obs, len_steps, th_tokens, allowance = self._construct_scratchpad_token_analysis(intermediate_steps)

        thoughts = ""
        i = 0
        for action, observation in intermediate_steps:
            thoughts += action.log
            # if (i > 0) or (drop_first == False):
            thoughts += f"\n{self.observation_prefix}{completion_enc.decode(completion_enc.encode(observation)[:len_obs[i]])}\n{self.llm_prefix}" 
            i += 1

        # print("\nNUM STEPS:",str(len_steps), "TH_TOKENS", th_tokens, "ALLOWANCE", allowance, "USED", len(completion_enc.encode(thoughts)), 'LEN_OBS', len_obs, "\n")            
        return thoughts


    def return_stopped_response(
        self,
        early_stopping_method: str,
        intermediate_steps: List[Tuple[AgentAction, str]],
        **kwargs: Any,
    ) -> AgentFinish:
        """Return response when agent has been stopped due to max iterations."""
        if early_stopping_method == "force":
            # `force` just returns a constant string
            return AgentFinish({"output": "Agent stopped due to max iterations."}, "")
        elif early_stopping_method == "generate":
            # Generate does one final forward pass
            thoughts = self._construct_scratchpad(intermediate_steps)
            new_inputs = {"agent_scratchpad": thoughts, "stop": self._stop}
            full_inputs = {**kwargs, **new_inputs}
            full_output = self.llm_chain.predict(**full_inputs)
            # We try to extract a final answer
            parsed_output = self._extract_tool_and_input(full_output)
            if parsed_output is None:
                # If we cannot extract, we just return the full output
                return AgentFinish({"output": full_output}, full_output)
            tool, tool_input = parsed_output
            if tool == self.finish_tool_name:
                # If we can extract, we send the correct stuff
                return AgentFinish({"output": tool_input}, full_output)
            else:
                # If we can extract, but the tool is not the final tool,
                # we just return the full output
                return AgentFinish({"output": full_output}, full_output)
        else:
            raise ValueError(
                "early_stopping_method should be one of `force` or `generate`, "
                f"got {early_stopping_method}"
            )


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

        if re_matches.group(1) == 'Finish':
            output = action_str.replace(action_prefix, '').replace('Finish', '').replace('<|im_end|>', '').strip()[1:-1]
            # print('output', output, '\n')
            return re_matches.group(1), output

        if re_matches is None:
            raise ValueError(f"Could not parse action directive: {action_str}")
        return re_matches.group(1), re_matches.group(2)





class ZSReAct(ZeroShotAgent, ModAgent):


    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "Observation: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "Thought:"


    @classmethod
    def create_prompt(
        cls,
        tools: Sequence[BaseTool],
        prefix: str = utils.langchain_helpers.mod_react_prompt.mod_react_prefix,
        suffix: str = utils.langchain_helpers.mod_react_prompt.mod_react_suffix,
        format_instructions: str = utils.langchain_helpers.mod_react_prompt.mod_react_format_instructions,
        input_variables: Optional[List[str]] = None,
        ) -> PromptTemplate:
        
        tool_strings = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
        tool_names = ", ".join([tool.name for tool in tools])

        format_instructions = utils.langchain_helpers.mod_react_prompt.mod_react_format_instructions.format(tool_names=tool_names)

        template = "\n\n".join([utils.langchain_helpers.mod_react_prompt.mod_react_prefix, tool_strings, format_instructions, 
                                utils.langchain_helpers.mod_react_prompt.mod_react_suffix])

        if input_variables is None:
            input_variables = ["input", "history", "agent_scratchpad"]

        return PromptTemplate(template=template, input_variables=input_variables)        




    def _extract_tool_and_input(self, text: str) -> Optional[Tuple[str, str]]:
        try:
            return self.get_action_and_input_mod(text)
        except Exception as e:
            # print("GOING TO FINAL ANSWER. EXCEPTION:", e, "\n")
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
            return "Final Answer", llm_output
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)
        return action, action_input.strip(" ").strip('"')



from langchain.agents.conversational_chat.prompt import (
    FORMAT_INSTRUCTIONS,
)

import utils.langchain_helpers.mod_ccr_prompt

from langchain.schema import (
    AgentAction,
    AIMessage,
    BaseLanguageModel,
    BaseMessage,
    BaseOutputParser,
    HumanMessage,
)

from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)

from langchain.chains import LLMChain
from langchain.callbacks.base import BaseCallbackManager


import json

class ModAgentOutputParser(BaseOutputParser):
    def get_format_instructions(self) -> str:
        return utils.langchain_helpers.mod_ccr_prompt.FORMAT_INSTRUCTIONS

    def parse(self, text: str) -> Any:
        cleaned_output = text.strip()
        if "```json" in cleaned_output:
            _, cleaned_output = cleaned_output.split("```json")
        if "```" in cleaned_output:
            cleaned_output, _ = cleaned_output.split("```")
        if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output[len("```json") :]
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output[len("```") :]
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[: -len("```")]
        if cleaned_output.startswith("``"):
            cleaned_output = cleaned_output[len("``") :]
        if cleaned_output.endswith("``"):
            cleaned_output = cleaned_output[: -len("``")]            

        # print("cleaned_output", cleaned_output) #TODO
        occurences = [
            "Human:",
            "AI:",
        ]

        for occ in occurences:
            cleaned_output = cleaned_output.replace(occ, '')

        # cleaned_output = cleaned_output.replace("'", '"')
        cleaned_output = cleaned_output.strip()
        # print("cleaned_output", cleaned_output) #TODO
        response = json.loads(cleaned_output)
        return {"action": response["action"], "action_input": response["action_input"]}



class ModConversationalChatAgent(ConversationalChatAgent, ModAgent):

    @classmethod
    def create_prompt(
        cls,
        tools: Sequence[BaseTool],
        system_message: str = utils.langchain_helpers.mod_ccr_prompt.PREFIX,
        human_message: str = utils.langchain_helpers.mod_ccr_prompt.SUFFIX,
        input_variables: Optional[List[str]] = None,
        output_parser: Optional[BaseOutputParser] = None,
    ) -> BasePromptTemplate:

        # assert False

        tool_strings = "\n".join(
            [f"> {tool.name}: {tool.description}" for tool in tools]
        )
        tool_names = ", ".join([tool.name for tool in tools])
        _output_parser = output_parser or ModAgentOutputParser()
        format_instructions = utils.langchain_helpers.mod_ccr_prompt.SUFFIX.format(
            format_instructions=_output_parser.get_format_instructions()
        )
        final_prompt = format_instructions.format(
            tool_names=tool_names, tools=tool_strings
        )
        if input_variables is None:
            input_variables = ["input", "chat_history", "agent_scratchpad"]

        system_start_prompt = "<|im_start|>system "
        user_start_prompt = "<|im_start|>user "
        assistant_start_prompt = "<|im_start|>assistant "
        end_prompt = "<|im_end|> "

        if CHOSEN_COMP_MODEL == 'gpt-35-turbo':
            prefix  = system_start_prompt + utils.langchain_helpers.mod_ccr_prompt.PREFIX + end_prompt + '\n' + user_start_prompt
            final_prompt = final_prompt + end_prompt + '\n' 

        messages = [
            SystemMessagePromptTemplate.from_template(utils.langchain_helpers.mod_ccr_prompt.PREFIX),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template(final_prompt),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]

        return ChatPromptTemplate(input_variables=input_variables, messages=messages)


    def _construct_scratchpad(
        self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> List[BaseMessage]:
        """Construct the scratchpad that lets the agent continue its thought process."""
        completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
        
        len_obs, len_steps, th_tokens, allowance = self._construct_scratchpad_token_analysis(intermediate_steps)

        thoughts: List[BaseMessage] = []
        thoughts_str = ''

        i = 0
        for action, observation in intermediate_steps:
            thoughts.append(AIMessage(content=action.log))
            thoughts_str += action.log
            observation = completion_enc.decode(completion_enc.encode(observation)[:len_obs[i]])
            human_message = HumanMessage(
                content=utils.langchain_helpers.mod_ccr_prompt.TEMPLATE_TOOL_RESPONSE.format(observation=observation)
            )
            thoughts_str += utils.langchain_helpers.mod_ccr_prompt.TEMPLATE_TOOL_RESPONSE.format(observation=observation)
            thoughts.append(human_message)
            i += 1

        # print("\nNUM STEPS:",str(len_steps), "TH_TOKENS", th_tokens, "ALLOWANCE", allowance, "USED", len(completion_enc.encode(thoughts_str)), 'LEN_OBS', len_obs, "\n")            
        return thoughts
        

        
    @classmethod
    def from_llm_and_tools(
        cls,
        llm: BaseLanguageModel,
        tools: Sequence[BaseTool],
        callback_manager: Optional[BaseCallbackManager] = None,
        system_message: str = utils.langchain_helpers.mod_ccr_prompt.PREFIX,
        human_message: str = utils.langchain_helpers.mod_ccr_prompt.SUFFIX,
        input_variables: Optional[List[str]] = None,
        output_parser: Optional[BaseOutputParser] = None,
        **kwargs: Any,
    ) -> Agent:
        """Construct an agent from an LLM and tools."""
        cls._validate_tools(tools)
        # print("output_parser", output_parser)
        _output_parser = output_parser or ModAgentOutputParser()
        prompt = cls.create_prompt(
            tools,
            system_message=system_message,
            human_message=human_message,
            input_variables=input_variables,
            output_parser=_output_parser,
        )
        llm_chain = LLMChain(
            llm=llm,
            prompt=prompt,
            callback_manager=callback_manager,
        )
        tool_names = [tool.name for tool in tools]
        return cls(
            llm_chain=llm_chain,
            allowed_tools=tool_names,
            output_parser=_output_parser,
            **kwargs,
        )