"""Callback Handler streams to stdout on new llm token."""
import sys
from typing import Any, Dict, List, Union
import re
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult


class StreamingSocketIOCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming. Only works with LLMs that support streaming."""

    def __init__(self, socketio_obj, connection_id):
        self.socketio_obj = socketio_obj
        self.connection_id = connection_id
        super().__init__()

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.buffer = ''
        self.partial_answer = ''
        self.num_partial_answer = 0

    def output_partial_answer(self):
        self.partial_answer = self.partial_answer.replace('":', '').replace('"', '').replace('}', '').replace('```', '').replace(':', '').replace('\\n', '<br>')
        self.socketio_obj.emit('token', self.partial_answer, to=self.connection_id)
        self.partial_answer = ''
        self.num_partial_answer = 0

    def process_new_token(self, token):
        self.partial_answer += token #
        self.num_partial_answer += 1

        source_matches = re.findall(r'\[(.*?)\]', self.partial_answer)
        for s in source_matches:
            self.partial_answer = self.partial_answer.replace('['+s+']', '')

        if ('[' in self.partial_answer) and (']' not in self.partial_answer):
            return
        else:
            if (self.num_partial_answer >= 5) and (not self.partial_answer.endswith('\\')):
                self.output_partial_answer()


    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled.""" 
        self.buffer += token

        if '"action": "Final Answer"' in self.buffer:               
            if '"action_input":' in self.buffer:
                self.process_new_token(token)

        if 'Final Answer:' in self.buffer:               
            self.process_new_token(token)


    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        self.output_partial_answer()

    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when LLM errors."""

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running."""

    def on_chain_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when chain errors."""

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when tool starts running.""" 

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Run on agent action."""

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when tool errors."""

    def on_text(self, text: str, **kwargs: Any) -> None:
        """Run on arbitrary text."""

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on agent end."""




class StreamingStdOutCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming. Only works with LLMs that support streaming."""

    buffer: str = ''
    partial_answer: str = ''
    num_partial_answer: int = 0


    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.buffer = ''
        self.partial_answer = ''
        self.num_partial_answer = 0


    def output_partial_answer(self):
        self.partial_answer = self.partial_answer.replace('":', '').replace('"', '').replace('}', '').replace('```', '').replace(':', '')
        sys.stdout.write(self.partial_answer)
        sys.stdout.flush()
        self.partial_answer = ''
        self.num_partial_answer = 0

    def process_new_token(self, token):
        self.partial_answer += token #
        self.num_partial_answer += 1

        source_matches = re.findall(r'\[(.*?)\]', self.partial_answer)
        for s in source_matches:
            self.partial_answer = self.partial_answer.replace('['+s+']', '')

        if ('[' in self.partial_answer) and (']' not in self.partial_answer):
            return
        else:
            if (self.num_partial_answer >= 5) and (not self.partial_answer.endswith('\\')):
                self.output_partial_answer()


    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled.""" 
        self.buffer += token

        if '"action": "Final Answer"' in self.buffer:               
            if '"action_input":' in self.buffer:
                self.process_new_token(token)

        if 'Final Answer:' in self.buffer:               
            self.process_new_token(token)


    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        self.output_partial_answer()



    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when LLM errors."""

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running."""

    def on_chain_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when chain errors."""

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when tool starts running."""

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Run on agent action."""
        pass

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when tool errors."""

    def on_text(self, text: str, **kwargs: Any) -> None:
        """Run on arbitrary text."""

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on agent end."""
