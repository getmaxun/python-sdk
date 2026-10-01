"""Describe what you want in plain English and let Maxun build the robot.

On Maxun Cloud nothing else is needed. On self-hosted Maxun an LLM is required:
set MAXUN_LLM_PROVIDER (anthropic, openai or ollama) and, for anthropic/openai,
MAXUN_LLM_API_KEY. This example passes them through only when they are set.
"""
import asyncio
import json
import os

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()

LLM = {
    k: v for k, v in {
        "llm_provider": os.environ.get("MAXUN_LLM_PROVIDER"),
        "llm_model": os.environ.get("MAXUN_LLM_MODEL"),
        "llm_api_key": os.environ.get("MAXUN_LLM_API_KEY"),
        "llm_base_url": os.environ.get("MAXUN_LLM_BASE_URL"),
    }.items() if v
}


async def main():
    async with Maxun() as maxun:
        # With a URL
        robot = await maxun.extract(
            "https://www.ycombinator.com/companies",
            prompt="Extract the first 15 company names, descriptions and batch",
            **LLM,
        )
        result = await robot.run()
        print(json.dumps(result.list_data[:3], indent=2))

        # Without a URL, Maxun searches for a suitable page first
        robot = await maxun.extract(
            prompt="Company names and descriptions from the Y Combinator companies directory",
            **LLM,
        )
        print(f"Robot built for {robot.url}")


asyncio.run(main())
