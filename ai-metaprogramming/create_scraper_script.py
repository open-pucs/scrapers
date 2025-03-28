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
from langchain_community.chat_models import ChatDeepInfra
from scrapegraphai.graphs import ScriptCreatorGraph

import logging

from concurrent.futures import ThreadPoolExecutor

from enum import Enum, auto

import asyncio

CHEAP_REGULAR_DEEPINFRA_MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

CHEAP_REASONING_DEEPINFRA_MODEL_NAME = "Qwen/QwQ-32B"

EXPENSIVE_DEEPINFRA_MODEL_NAME = "deepseek-ai/DeepSeek-R1-Turbo"

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY", None)

default_logger = logging.getLogger(__name__)


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
    if DEEPINFRA_API_KEY is None:
        raise ValueError("DeepInfra API token not provided")

    llm_instance = ChatDeepInfra(
        model=model_name, deepinfra_api_token=DEEPINFRA_API_KEY
    )
    return llm_instance


def create_graph_config() -> Dict[str, Any]:
    config = {
        "llm": {
            "model_instance": get_deepinfra_llm(ModelType.CHEAP_REASONING),
            "model_tokens": 10240,  # Default context window for Llama-2
        },
        "library": "playwright",
    }

    # Add common configuration

    return config


async def run_pipeline(url: str) -> str:
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
    default_logger.info(
        "Configuration initialized, beginning script creator graph processing"
    )

    # Create executor for running sync code in threads
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Step 1: Initial Reconnaissance
        recon_graph = ScriptCreatorGraph(
            prompt=load_prompt(recon_prompt_path, {"url": url}),
            source=url,
            config=config,
        )
        # Run in thread and get future
        schema_future = executor.submit(recon_graph.run)

        # Wait for schema before creating scraper
        schema = await asyncio.get_event_loop().run_in_executor(
            None, schema_future.result
        )

        # Step 2: Create Initial Scraper
        create_graph = ScriptCreatorGraph(
            prompt=load_prompt(
                make_scraper_prompt_path, {"schema": schema, "url": url}
            ),
            source=url,
            config=config,
        )
        # Run in thread and get future
        scraper_future = executor.submit(create_graph.run)

        # Wait for scraper
        initial_scraper = await asyncio.get_event_loop().run_in_executor(
            None, scraper_future.result
        )

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


async def spin():
    """Display an animated spinner while processing."""
    symbols = itertools.cycle(["-", "/", "|", "\\"])
    while True:
        sys.stdout.write("\r" + next(symbols) + " Processing...")
        sys.stdout.flush()
        await asyncio.sleep(0.1)


async def main_async(url: str) -> str:
    """Run the pipeline with spinner animation."""
    spinner_task = asyncio.create_task(spin())
    try:
        result = await run_pipeline(url)
    finally:
        spinner_task.cancel()
    return result


def rand_string() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(8)).decode()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate web scraper script.")
    parser.add_argument("--url", type=str, help="URL to scrape")
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
    if args.deepinfra_api_key is not None:
        DEEPINFRA_API_KEY = args.deepinfra_api_key
    if DEEPINFRA_API_KEY is None:
        DEEPINFRA_API_KEY = input("Please enter your DeepInfra API token: ")

    # Run the pipeline with spinner
    print("\nGenerating scraper...")
    try:
        result = asyncio.run(main_async(url))
    except Exception as e:
        print(f"\nError: {e}")
        return 1

    # Set up output directory
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    # Generate filename components
    sanitized_url = re.sub(r"[^a-zA-Z0-9]", "_", url)[:50]  # Limit length
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"scraper_{sanitized_url}_{date_str}_.py"
    output_path = output_dir / filename
    # Save the result
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
    except IOError as e:
        print(f"\nError saving file: {e}")
        return 1

    print(
        f"\nCongratulations! The scraper has been saved to:\n{output_path.resolve()}\n"
    )
    return 0


if __name__ == "__main__":
    exit(main())
