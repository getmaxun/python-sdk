"""
List Pagination Example

This example demonstrates:
- Extracting lists with capture_list
- Handling pagination automatically
- Different pagination strategies
- Setting max_items limit

Site: GitHub Repositories (https://github.com/ab?tab=repositories)
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

    # Extract repositories from GitHub. Auto-detects clickNext pagination.
    robot = await (
        extractor
        .create("GitHub Repositories (AB)")
        .navigate("https://github.com/ab?tab=repositories")
        .capture_list(
            {
                "selector": "li.col-12.d-flex.flex-justify-between.width-full"
                            ".py-4.border-bottom.color-border-muted.public.source",
                "maxItems": 100,
            }
        )
    )

    print(f"Robot created: {robot.id}")

    result = await robot.run()

    list_data = result.get("data", {}).get("listData") or []
    print(f"\nExtracted {len(list_data)} repositories")
    print("\nFirst 3 repositories:")
    print(json.dumps(list_data[:3], indent=2))

    # -------------------------------------------------------------------------
    # Other pagination examples (uncomment to use):
    #
    # Infinite scroll (Reddit, Twitter, etc.)
    # .capture_list({
    #     "selector": ".post",
    #     "pagination": {"type": "scrollDown"},
    #     "maxItems": 50,
    # })
    #
    # Click "Next" button (traditional pagination)
    # .capture_list({
    #     "selector": ".product-item",
    #     "pagination": {"type": "clickNext", "selector": ".pagination-next"},
    #     "maxItems": 100,
    # })
    #
    # Click "Load More" button
    # .capture_list({
    #     "selector": ".article",
    #     "pagination": {"type": "clickLoadMore", "selector": "button.load-more"},
    #     "maxItems": 30,
    # })
    # -------------------------------------------------------------------------


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
