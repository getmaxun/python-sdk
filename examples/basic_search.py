"""
Search Example

This example demonstrates:
- Using the Search SDK to search the web and scrape results
- Configuring search mode (discover vs scrape)
- Setting search filters (time range, region)
- Limiting search results

Provider: DuckDuckGo
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from maxun import Search, Config, SearchConfig


async def main():
    searcher = Search(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "http://localhost:8080/api/sdk"),
    ))

    robot = await searcher.create(
        "Tech News Search",
        SearchConfig(
            query="latest AI developments 2025",
            mode="discover",
            filters={"timeRange": "week"},
            limit=10,
        ),
    )

    print(f"Search robot created: {robot.id}")

    result = await robot.run()

    search_data = (result.get("data") or {}).get("searchData")

    if isinstance(search_data, dict):
        all_results = []
        for value in search_data.values():
            if isinstance(value, list):
                all_results.extend(value)
            elif isinstance(value, dict) and isinstance(value.get("results"), list):
                all_results.extend(value["results"])

        print(f"Search results found: {len(all_results)}")
        print("\nSearch Results:")
        for i, item in enumerate(all_results, 1):
            print(f"\n  {i}. {item.get('title') or 'No title'}")
            print(f"     URL: {item.get('url') or 'No URL'}")
            description = item.get("description")
            if description:
                print(f"     Description: {description[:150]}...")

    elif isinstance(search_data, list):
        print(f"Search results found: {len(search_data)}")
        print("\nSearch Results:")
        for i, item in enumerate(search_data, 1):
            print(f"\n  {i}. {item.get('title') or 'No title'}")
            print(f"     URL: {item.get('url') or 'No URL'}")


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
