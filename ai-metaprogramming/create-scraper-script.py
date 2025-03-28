import argparse
import os
from pathlib import Path
from typing import Optional, Dict, Any
from langchain_community.chat_models import ChatDeepInfra
from scrapegraphai.graphs import ScriptCreatorGraph

from enum import Enum, auto

import asyncio

CHEAP_REGULAR_DEEPINFRA_MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

CHEAP_REASONING_DEEPINFRA_MODEL_NAME = "Qwen/QwQ-32B"

EXPENSIVE_DEEPINFRA_MODEL_NAME = "deepseek-ai/DeepSeek-R1-Turbo"

DEEPINFRA_API_TOKEN = os.getenv("DEEPINFRA_API_TOKEN", None)


def load_prompt(prompt_file: Path, format_dict: Dict[str, Any] = {}) -> str:
    """Load prompt content from a markdown file."""
    with open(prompt_file, "r") as f:
        results = f.read()
        return results.format(**format_dict)


class ModelType(Enum):
    CHEAP_REGULAR = auto()
    CHEAP_REASONING = auto()
    EXPENSIVE = auto()


def get_deepinfra_llm(model_name: str | ModelType) -> ChatDeepInfra:
    if isinstance(model_name, ModelType):
        match model_name:
            case ModelType.CHEAP_REGULAR:
                model_name = CHEAP_REGULAR_DEEPINFRA_MODEL_NAME
            case ModelType.CHEAP_REASONING:
                model_name = CHEAP_REASONING_DEEPINFRA_MODEL_NAME
            case ModelType.EXPENSIVE:
                model_name = EXPENSIVE_DEEPINFRA_MODEL_NAME
    if DEEPINFRA_API_TOKEN is None:
        raise ValueError("DeepInfra API token not provided")

    llm_instance = ChatDeepInfra(
        model=model_name, deepinfra_api_token=DEEPINFRA_API_TOKEN
    )
    return llm_instance


def create_graph_config() -> Dict[str, Any]:
    config = {
        "llm": {
            "model_instance": get_deepinfra_llm(ModelType.CHEAP_REASONING),
            "model_tokens": 10240,  # Default context window for Llama-2
        },
        "library": "selenium",
    }

    # Add common configuration

    return config


async def run_pipeline(url: str, instructions: Optional[str] = None) -> str:
    """Run the full pipeline to generate a scraper."""
    current_dir = Path(__file__).parent

    # Load all prompts
    recon_prompt_path = current_dir / "initial-recognisance-prompt.md"
    make_scraper_prompt_path = current_dir / "make-scraper-prompt.md"
    adapter_prompt_path = current_dir / "write_generic_adapters_prompt.md"
    refactor_prompt_path = current_dir / "refactor_prompt.md"
    final_prompt_path = current_dir / "final_recombine_prompt.md"

    # Create base configuration
    config = create_graph_config()

    # Step 1: Initial Reconnaissance
    recon_graph = ScriptCreatorGraph(
        prompt=load_prompt(recon_prompt_path, {"url": url}),
        source=url,
        config=config,
    )
    schema = recon_graph.run()

    # Step 2: Create Initial Scraper
    create_graph = ScriptCreatorGraph(
        prompt=load_prompt(make_scraper_prompt_path, {"schema": schema, "url": url}),
        source=url,
        config=config,
        # schema=schema_result,
    )
    initial_scraper = create_graph.run()

    thoughtful_llm = get_deepinfra_llm(ModelType.EXPENSIVE)

    async def get_adapters():
        adapter_message = load_prompt(adapter_prompt_path, {"schemas": schema})
        adapters_response = await thoughtful_llm.ainvoke(adapter_message)
        return adapters_response.content

    async def get_refactored():
        refactor_message = load_prompt(
            refactor_prompt_path, {"scrapers": initial_scraper}
        )
        refactor_response = await thoughtful_llm.ainvoke(refactor_message)
        return refactor_response.content

    adapters, refactored = await asyncio.gather(get_adapters(), get_refactored())

    # Step 5: Final Recombination
    final_message = load_prompt(
        final_prompt_path, {"adapters": adapters, "scrapers": refactored}
    )
    final_response = await thoughtful_llm.ainvoke(final_message)
    final_result = final_response.content

    if not isinstance(final_result, str):
        raise ValueError(
            "Final result is not a string. Please check your prompt and try again."
        )

    return final_result


def main():
    # could you implement a cli tool on this, so that when this script is run, it prompts the user for a url, displays a loading animation while it runs the pipeline, when successful it displays a congradulations message to the user and saves the file in a new path with the url, date and random id?
    pass


if __name__ == "__main__":
    exit(main())
