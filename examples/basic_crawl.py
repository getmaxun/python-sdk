"""
Crawl Example

This example demonstrates:
- Using the Crawl SDK to discover and scrape multiple pages
- Configuring crawl scope (domain, subdomain, or path)
- Setting limits and depth for crawling
- Using sitemap discovery
- Filtering pages with include/exclude paths

Site: Y Combinator Jobs (https://www.ycombinator.com/jobs)
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from maxun import Crawl, Config, CrawlConfig


async def main():
    crawler = Crawl(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "https://app.maxun.dev/api/sdk/"),
    ))

    robot = await crawler.create(
        "YC Companies Crawler",
        "https://www.ycombinator.com/jobs",
        CrawlConfig(
            mode="domain",
            limit=10,
            max_depth=3,
            include_paths=[],
            exclude_paths=[],
            use_sitemap=True,
            follow_links=True,
            respect_robots=True,
        ),
    )

    print(f"Crawl robot created: {robot.id}")
    print("Starting crawl...")

    result = await robot.run()

    print("\n=== Crawl Completed ===")
    print(f"Status: {result.get('status')}")
    print(f"Run ID: {result.get('runId')}")

    crawl_data = (result.get("data") or {}).get("crawlData")

    if crawl_data:
        if isinstance(crawl_data, dict):
            all_pages = []
            for value in crawl_data.values():
                if isinstance(value, list):
                    all_pages.extend(value)

            print(f"Pages crawled: {len(all_pages)}")
            print("\nCrawled URLs:")
            for i, page in enumerate(all_pages, 1):
                url = (page.get("metadata") or {}).get("url") or page.get("url") or f"Page {i}"
                print(f"  {i}. {url}")
                if (page.get("metadata") or {}).get("title"):
                    print(f"     Title: {page['metadata']['title']}")
                if page.get("wordCount"):
                    print(f"     Words: {page['wordCount']}")

        elif isinstance(crawl_data, list):
            print(f"Pages crawled: {len(crawl_data)}")
            print("\nCrawled URLs:")
            for i, page in enumerate(crawl_data, 1):
                url = (page.get("metadata") or {}).get("url") or page.get("url") or f"Page {i}"
                print(f"  {i}. {url}")
        else:
            print(f"Crawl data format: {type(crawl_data)}")
            print(f"Crawl data: {json.dumps(crawl_data, indent=2)}")
    else:
        print("No crawl data found")
        print(f"Result data keys: {list((result.get('data') or {}).keys())}")


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
