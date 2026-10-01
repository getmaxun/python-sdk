"""Pick specific values off a page with CSS selectors."""
import asyncio
import json

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await (
            maxun.extract("Hacker News Top Story", "https://news.ycombinator.com")
            .capture_text({
                "Title": "tr.athing:first-child .titleline > a",
                "Points": "tr.athing:first-child + tr .score",
                "Author": "tr.athing:first-child + tr .hnuser",
            })
            .build()
        )
        result = await robot.run()
        print(json.dumps(result.text_data, indent=2))


asyncio.run(main())
