import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any
from scrapegraphai.graphs import ScriptCreatorGraph


def load_prompt(prompt_file: str) -> str:
    """Load prompt content from a markdown file."""
    with open(prompt_file, "r") as f:
        return f.read()


def create_graph_config(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Create the graph configuration."""
    if not api_key:
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key must be provided either through --api-key argument "
                "or OPENAI_API_KEY environment variable"
            )

    config = {
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": api_key,
            "temperature": 0.7,
        },
        "library": "beautifulsoup4",
    }
    return config


def run_pipeline(url: str, instructions: Optional[str] = None) -> str:
    """Run the full pipeline to generate a scraper."""
    current_dir = Path(__file__).parent

    # Load all prompts
    recon_prompt = load_prompt(current_dir / "initial-recognisance-prompt.md")
    create_prompt = load_prompt(current_dir / "create-scraper-prompt.md")
    adapter_prompt = load_prompt(current_dir / "write_generic_adapters_prompt.md")
    refactor_prompt = load_prompt(current_dir / "refactor_prompt.md")
    final_prompt = load_prompt(current_dir / "final_recombine_prompt.md")

    # Create base configuration
    config = create_graph_config()

    # Step 1: Initial Reconnaissance
    recon_graph = ScriptCreatorGraph(
        prompt=f"{recon_prompt}\nAnalyze this PUC website: {url}\n{instructions or ''}",
        source=url,
        config=config,
    )
    schema_result = recon_graph.run()

    # Step 2: Create Initial Scraper
    create_graph = ScriptCreatorGraph(
        prompt=f"{create_prompt}\nCreate a scraper for: {url}\nUsing schema:\n{schema_result}\n{instructions or ''}",
        source=url,
        config=config,
        schema=schema_result,
    )
    initial_scraper = create_graph.run()

    # Step 3: Create Generic Adapters
    adapter_graph = ScriptCreatorGraph(
        prompt=f"{adapter_prompt}\nCreate adapters for this scraper:\n{initial_scraper}\n{instructions or ''}",
        source=url,
        config=config,
    )
    adapters = adapter_graph.run()

    # Step 4: Refactor
    refactor_graph = ScriptCreatorGraph(
        prompt=f"{refactor_prompt}\nRefactor this code:\n{initial_scraper}\n{adapters}\n{instructions or ''}",
        source=url,
        config=config,
    )
    refactored = refactor_graph.run()

    # Step 5: Final Recombination
    final_graph = ScriptCreatorGraph(
        prompt=f"{final_prompt}\nFinalize this scraper:\n{refactored}\n{instructions or ''}",
        source=url,
        config=config,
    )
    final_result = final_graph.run()

    return final_result


def main():
    parser = argparse.ArgumentParser(
        description="Generate a PUC website scraper",
        epilog="Note: OpenAI API key must be provided either through --api-key argument or OPENAI_API_KEY environment variable",
    )
    parser.add_argument("url", help="URL of the PUC website to scrape")
    parser.add_argument(
        "--instructions",
        "-i",
        help="Additional instructions for the scraper generation",
    )
    parser.add_argument("--output", "-o", help="Output file for the generated scraper")
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (defaults to OPENAI_API_KEY environment variable)",
    )

    args = parser.parse_args()

    try:
        # Create config first to validate API key
        config = create_graph_config(args.api_key)
        result = run_pipeline(args.url, args.instructions)

        if args.output:
            with open(args.output, "w") as f:
                f.write(result)
            print(f"Scraper written to {args.output}")
        else:
            print(result)

    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1
    except Exception as e:
        print(f"Error generating scraper: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
