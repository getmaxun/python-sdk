"""
Chained Multi-Step Extraction Example

This example demonstrates:
- Multi-step navigation workflows
- Combining captureText and captureList on the same page
- Building complex scraping pipelines

Site: BBC Sport — Premier League table (https://www.bbc.com/sport/football/tables)
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

    robot = await (
        extractor
        .create("Premier League Score Table")
        .navigate("https://www.bbc.com/sport/football/tables")
        .capture_text(
            {"Title": "a#tab-PremierLeague"},
            "Text Data",
        )
        .capture_list(
            {
                "selector": "tr.ssrcss-1urqilq-CellsRow.e13j9mpy2",
                "maxItems": 10,
            },
            "Football Scores",
        )
    )

    print(f"Robot created: {robot.id}")

    result = await robot.run()

    print("\n=== Featured Tab ===")
    print(result.get("data", {}).get("textData"))

    list_data = result.get("data", {}).get("listData") or []
    print(f"\n=== League Table ({len(list_data)} rows) ===")
    print("First 3 rows:")
    print(json.dumps(list_data[:3], indent=2))


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
