"""Ask an LLM a question about a page on every run (Smart Queries).

Maxun Cloud runs the LLM for you. On self-hosted Maxun, pass llm_provider=...
(plus llm_api_key for anthropic/openai) to maxun.scrape().
"""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.scrape(
            "https://news.ycombinator.com",
            smart_queries="Which story on this page has the most points?",
        )
        result = await robot.run()
        print(result.smart_query_result)

        # A different question for one run only:
        result = await robot.run(smart_queries="List the three newest stories.")
        print(result.smart_query_result)


asyncio.run(main())
