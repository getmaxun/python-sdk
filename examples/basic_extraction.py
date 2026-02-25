"""
Basic Extraction Example

This example demonstrates:
- Creating a robot with capture_text
- Extracting specific fields from a single page
- Running the robot and retrieving results

Site: Hacker News (https://news.ycombinator.com)
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
        base_url=os.environ.get("MAXUN_BASE_URL", "https://app.maxun.dev/"),
    ))

    # Extract top story from Hacker News
    robot = await (
        extractor
        .create("Hacker News Top Story")
        .navigate("https://news.ycombinator.com")
        .capture_text({
            "Title": "tr.athing:first-child .titleline > a",
            "Points": "tr.athing:first-child + tr .score",
            "Author": "tr.athing:first-child + tr .hnuser",
            "Posted": "tr.athing:first-child + tr .age a",
        })
    )

    print(f"Robot created: {robot.id}")

    result = await robot.run()

    print(result)

    print("\nExtracted Hacker News Top Story:")
    print(json.dumps(result.get("data", {}).get("textData"), indent=2))


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
