"""
LLM-based Extraction Example

This example demonstrates:
- Using natural language prompts to extract data
- LLM automatically generates the extraction workflow
- Support for multiple LLM providers (Ollama, Anthropic, OpenAI)
- Creates a reusable robot that can be executed anytime
- Auto-search: when no URL is provided the system finds the site automatically

Site: Y Combinator Companies (https://www.ycombinator.com/companies)
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from maxun import Extract, Config


async def main():
    extractor = Extract(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "http://localhost:8080/api/sdk"),
    ))

    print("Example 1: Creating robot with configured URL...\n")

    robot = await extractor.extract(
        url="https://www.ycombinator.com/companies",
        prompt="Extract the first 15 YC company names, their descriptions, and batch information",
        llm_provider="ollama",
        llm_model="llama3.2-vision",
        llm_base_url="http://localhost:11434",
        robot_name="YC Companies LLM Extractor",
    )

    print(f"Robot created: {robot.id}")

    print("Executing robot...\n")
    result = await robot.run()

    list_data = result.get("data", {}).get("listData") or []
    print("Extraction completed!")
    print(f"  Status: {result.get('status')}")
    print(f"  Companies extracted: {len(list_data)}\n")

    print("First 3 companies:")
    print(json.dumps(list_data[:3], indent=2))

    print("\n\nExample 2: Creating robot without configured URL...\n")

    auto_search_robot = await extractor.extract(
        prompt="Extract company names and descriptions from the YCombinator Companies page",
        llm_provider="ollama",
        robot_name="YC Auto-Search Extractor",
    )

    print(f"Auto-search robot created: {auto_search_robot.id}")

    print("Executing robot...\n")
    auto_result = await auto_search_robot.run()

    auto_list = auto_result.get("data", {}).get("listData") or []
    print("Extraction completed!")
    print(f"  Status: {auto_result.get('status')}")
    print(f"  Companies extracted: {len(auto_list)}\n")

    print("First 3 companies:")
    print(json.dumps(auto_list[:3], indent=2))

    # -------------------------------------------------------------------------
    # For Anthropic (recommended for best results):
    #   llm_provider="anthropic",
    #   llm_model="claude-3-5-sonnet-20241022",
    #   llm_api_key=os.environ["ANTHROPIC_API_KEY"],
    #
    # For OpenAI:
    #   llm_provider="openai",
    #   llm_model="gpt-4-vision-preview",
    #   llm_api_key=os.environ["OPENAI_API_KEY"],
    # -------------------------------------------------------------------------


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
