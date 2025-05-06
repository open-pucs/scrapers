import enum
import logging
import sys
from enum import Enum
from typing import Optional

from langchain_community.chat_models import ChatDeepInfra
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser

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


def make_sysmsg(content: str) -> SystemMessage:
    return SystemMessage(content=content)


def strip_thinking(content: str) -> str:
    return content.split("</think>")[-1].strip()


def get_chat_llm_from_model_name(model_name: LlmName = LlmName.Regular):
    model_str = to_deepinfra_model_name(model_name)
    api_key = DEEPINFRA_API_KEY
    assert api_key, "Deepinfra API key must be configured"
    return ChatDeepInfra(
        model=model_str,
        deepinfra_api_key=api_key,
        temperature=0.5,
        max_tokens=50,
        top_p=0.9,
    ).bind(stop=["</think>"])


def create_llm_chain(system_prompt: str, model_name: LlmName = LlmName.Regular):
    llm = get_chat_llm_from_model_name(model_name)
    return (
        {
            "system": lambda _: SystemMessage(content=system_prompt),
            "prompt": lambda x: x["prompt"],
        }
        | llm
        | StrOutputParser()
    )
