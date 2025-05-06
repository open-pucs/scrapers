import enum
import logging
import sys


from typing import Optional

from llama_index.core.prompts import ChatMessage
from llama_index.llms.deepinfra import DeepInfraLLM
import asyncio
from enum import Enum

from openpuc_scrapers.models.constants import DEEPINFRA_API_KEY


class LlmName(str, Enum):
    Regular = "regular"
    CheapReasoning = "cheap-reasoning"
    ExpensiveReasoning = "expensive-reasoning"


def to_deepinfra_model_name(name: LlmName) -> str:
    match name:
        case LlmName.Regular:
            return "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
        case LlmName.CheapReasoning:
            return "Qwen/Qwen3-32B"
        case LlmName.ExpensiveReasoning:
            return "deepseek-ai/DeepSeek-R1-Turbo"


default_logger = logging.getLogger(__name__)


def make_sysmsg(content: str) -> ChatMessage:
    return ChatMessage(content=content, role="system")


def strip_thinking(content: str) -> str:
    return content.split("</think>")[-1].strip()


def get_chat_llm_from_model_name(model_name: LlmName = LlmName.Regular):
    model_str = to_deepinfra_model_name(model_name)
    assert DEEPINFRA_API_KEY is not None, "Deepinfra API key was none"
    assert DEEPINFRA_API_KEY == "", "Deepinfra api key was the empty string."
    return DeepInfraLLM(
        model=model_str,
        api_key=DEEPINFRA_API_KEY,
        temperature=0.5,
        max_tokens=50,
        additional_kwargs={"top_p": 0.9},
    )
