import argparse
import base64
from datetime import datetime
import os
from pathlib import Path
import re
import secrets
import sys
import itertools
from typing import Optional, Dict, Any
from langchain.chat_models.base import BaseChatModel
from langchain_community.chat_models import ChatDeepInfra
from langchain_core.language_models import LLM
from pydantic import BaseModel
from scrapegraphai.graphs import ScriptCreatorGraph
import traceback

from jinja2 import Environment, FileSystemLoader, select_autoescape
import logging

from concurrent.futures import ThreadPoolExecutor

from enum import Enum, auto

import asyncio
from langchain_core.messages import BaseMessage


def raise_helper(msg):
    raise Exception(msg)


env = Environment(loader=FileSystemLoader("./prompts"), autoescape=select_autoescape())
env.globals["raise"] = raise_helper

CHEAP_REGULAR_DEEPINFRA_MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

CHEAP_REASONING_DEEPINFRA_MODEL_NAME = "Qwen/QwQ-32B"

EXPENSIVE_REASONING_DEEPINFRA_MODEL_NAME = "deepseek-ai/DeepSeek-R1-Turbo"

EXPENSIVE_REGULAR_DEEPINFRA_MODEL_NAME = "deepseek-ai/DeepSeek-V3-0324"

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY", None)

default_logger = logging.getLogger(__name__)
default_logger.setLevel(logging.DEBUG)
default_logger.addHandler(logging.StreamHandler(sys.stdout))
default_logger.addHandler(logging.StreamHandler(sys.stderr))


def load_prompt(prompt_file: Path, format_dict: Dict[str, Any] = {}) -> str:
    """Load prompt content from a markdown file."""
    try:
        with open(prompt_file, "r") as f:
            results = f.read()
    except Exception as e:
        default_logger.error(
            f"Failed to load prompt file, {prompt_file} with error: {e}"
        )
        raise e
    if format_dict == {}:
        return results
    try:
        return results.format(**format_dict)
    except Exception as e:
        default_logger.error(f"Failed to format prompt: {e}\nPrompt: {results}")
        raise e


class ModelType(Enum):
    CHEAP_REGULAR = auto()
    CHEAP_REASONING = auto()
    EXPENSIVE_REGULAR = auto()
    EXPENSIVE_REASONING = auto()


def get_deepinfra_llm(
    model_name: str | ModelType, max_tokens: int = 20480
) -> ChatDeepInfra:
    if isinstance(model_name, ModelType):
        match model_name:
            case ModelType.CHEAP_REGULAR:
                model_name = CHEAP_REGULAR_DEEPINFRA_MODEL_NAME
            case ModelType.CHEAP_REASONING:
                model_name = CHEAP_REASONING_DEEPINFRA_MODEL_NAME
            case ModelType.EXPENSIVE_REASONING:
                model_name = EXPENSIVE_REASONING_DEEPINFRA_MODEL_NAME
            case ModelType.EXPENSIVE_REGULAR:
                model_name = EXPENSIVE_REGULAR_DEEPINFRA_MODEL_NAME
    if DEEPINFRA_API_KEY is None:
        raise ValueError("DeepInfra API token not provided")

    llm_instance = ChatDeepInfra(
        model=model_name, deepinfra_api_token=DEEPINFRA_API_KEY, max_tokens=max_tokens
    )
    return llm_instance


def discard_llm_thoughts(thoughtful_code: str | BaseMessage, warn: bool = True) -> str:
    if not isinstance(thoughtful_code, str):
        thoughtful_code = str(thoughtful_code.content)
    split_thoughts = thoughtful_code.split("</think>")
    if len(split_thoughts) != 2:
        if warn:
            default_logger.warning(
                f"Response didnt have the structure we anticipated, we detected {len(split_thoughts)-1} instances of the </think> tag."
            )
        return thoughtful_code
    return split_thoughts[1]


def create_graph_config(llm: BaseChatModel, max_tokens: int = 10240) -> Dict[str, Any]:
    config = {
        "llm": {"model_instance": llm, "model_tokens": max_tokens},
        "library": "playwright",
    }

    # Add common configuration

    return config


class ScrapegraphOutput(BaseModel):
    scraper_code: str
    schemas: str


async def handle_scrapegraph_creation(
    url: str, llm: BaseChatModel
) -> ScrapegraphOutput:
    recon_prompt_template = env.get_template("initial_recognisance_prompt.md")
    make_scraper_template = env.get_template("make_scraper_prompt.md")

    # Create base configuration
    config = create_graph_config(llm)
    default_logger.error(
        "Configuration initialized, beginning script creator graph processing"
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        default_logger.debug("Creating initial reconnaissance graph")
        # Step 1: Initial Reconnaissance
        recon_graph = ScriptCreatorGraph(
            prompt=recon_prompt_template.render(url=url),
            source=url,
            config=config,
        )
        default_logger.debug("Submitting reconnaissance task to executor")
        # Run in thread and get future
        schema_future = executor.submit(recon_graph.run)

        default_logger.debug("Waiting for schema result")
        # Wait for schema before creating scraper
        schema = await asyncio.get_event_loop().run_in_executor(
            None, schema_future.result
        )
        default_logger.debug(f"Schema result: {schema}")

        default_logger.debug("Creating initial scraper graph")
        # Step 2: Create Initial Scraper
        create_graph = ScriptCreatorGraph(
            prompt=make_scraper_template.render(url=url, schema=schema),
            source=url,
            config=config,
        )
        default_logger.debug("Submitting scraper creation task to executor")
        # Run in thread and get future
        scraper_future = executor.submit(create_graph.run)

        default_logger.debug("Waiting for initial scraper result")
        # Wait for scraper
        initial_scraper = await asyncio.get_event_loop().run_in_executor(
            None, scraper_future.result
        )
        return ScrapegraphOutput(scraper_code=initial_scraper, schemas=schema)


class ScraperOutputs(BaseModel):
    schemas: str = ""
    initial_scraper: str = ""
    adapters: str = ""
    refactored_scraper: str = ""
    final: str = ""


async def refactor_scrapegraph(
    inputs: ScrapegraphOutput, llm: BaseChatModel
) -> ScraperOutputs:
    schema = discard_llm_thoughts(inputs.schemas, warn=False)
    initial_scraper = discard_llm_thoughts(inputs.scraper_code, warn=False)
    output = ScraperOutputs(schemas=schema, initial_scraper=initial_scraper)

    adapter_prompt_template = env.get_template("generic_adapters_prompt.md")
    refactor_prompt_template = env.get_template("refactor_prompt.md")
    final_prompt_template = env.get_template("final_recombine_prompt.md")

    default_logger.debug("Creating adapter and refactoring graph")

    default_logger.info("succesfuly created llm")

    async def get_adapters() -> str:
        default_logger.debug(
            f"Loading adapter refactoring prompt with schemas: {schema}"
        )
        adapter_message = adapter_prompt_template.render(schemas=schema)
        default_logger.debug(f"Adapter message: {adapter_message}")
        adapters_response = await llm.ainvoke(adapter_message)
        default_logger.debug(f"Adapters response: {adapters_response.content}")
        return discard_llm_thoughts(adapters_response)

    async def get_refactored():
        # NOTE: THIS SHOULD BE RUN IN PARALLEL FOR EACH INDIVIDUAL WEBSITE PAGE
        default_logger.debug(f"Loading scraper refactoring prompt")
        refactor_message = refactor_prompt_template.render(scrapers=initial_scraper)
        refactor_response = await llm.ainvoke(refactor_message)
        return discard_llm_thoughts(refactor_response)

    adapters, refactored = await asyncio.gather(get_adapters(), get_refactored())
    output.adapters = adapters
    output.refactored_scraper = refactored

    # Step 5: Final Recombination
    final_message = final_prompt_template.render(
        adapters=adapters, scrapers=refactored, schemas=schema
    )
    final_response = await llm.ainvoke(final_message)
    final_result = discard_llm_thoughts(final_response)
    output.final = final_result

    return output


def save_scraper_output(
    scraper_output: ScraperOutputs, output_dir: Path, url: str
) -> None:
    # Set up output directory
    output_dir.mkdir(exist_ok=True)
    # Generate filename components
    sanitized_url = re.sub(r"[^a-zA-Z0-9]", "_", url)[:50]  # Limit length
    date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"scraper_{sanitized_url}_{date_str}_{rand_string()}"
    scraper_dir = output_dir / folder_name
    scraper_dir.mkdir(exist_ok=True)

    # Save the final result
    result_path = scraper_dir / "result.py"
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(scraper_output.final)

    # Save intermediate outputs
    intermediate_path = scraper_dir / "intermediate.json"
    with open(intermediate_path, "w", encoding="utf-8") as f:
        f.write(scraper_output.model_dump_json(indent=2))

    print(
        f"\nCongratulations! The scraper has been saved to:\n{scraper_dir.resolve()}\n"
    )


async def run_pipeline(url: str) -> ScraperOutputs:
    """Run the full pipeline to generate a scraper."""
    thoughtful_llm = get_deepinfra_llm(ModelType.CHEAP_REASONING)
    regular_llm = get_deepinfra_llm(ModelType.CHEAP_REGULAR)

    scrapegraph_intermediate = await handle_scrapegraph_creation(url, regular_llm)
    result = await refactor_scrapegraph(scrapegraph_intermediate, thoughtful_llm)
    save_scraper_output(result, Path("outputs"), url)
    return result


async def spin():
    """Display an animated spinner while processing."""
    symbols = itertools.cycle(["-", "/", "|", "\\"])
    while True:
        sys.stdout.write("\r" + next(symbols) + " Processing...")
        sys.stdout.flush()
        await asyncio.sleep(0.1)


async def main_async(url: str) -> None:
    """Run the pipeline with spinner animation."""
    spinner_task = asyncio.create_task(spin())
    try:
        await run_pipeline(url)
    finally:
        spinner_task.cancel()


def rand_string() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(8)).decode()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate web scraper script.")
    parser.add_argument("--url", type=str, help="URL to scrape")
    parser.add_argument("--deepinfra", type=str, help="Override DeepInfra API key")
    args = parser.parse_args()

    # Get URL from args or prompt
    url = args.url
    if not url:
        url = input("Please enter the URL to scrape: ")

    # Validate URL format
    if not url.startswith(("http://", "https://")):
        print("Error: Invalid URL. Must start with http:// or https://")
        return 1
    global DEEPINFRA_API_KEY
    if args.deepinfra is not None:
        DEEPINFRA_API_KEY = args.deepinfra_api_key
    if DEEPINFRA_API_KEY is None:
        DEEPINFRA_API_KEY = input("Please enter your DeepInfra API key: ")

    # Run the pipeline with spinner
    print("\nGenerating scraper...")
    try:
        result = asyncio.run(main_async(url))
    except Exception as e:

        print(f"\nError: {e}")
        print("\nTraceback:")
        print(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
