"""
Simple Scraping Example

This example demonstrates:
- Using the Scrape SDK for simple page scraping
- Getting page content in markdown and HTML formats
- Capturing page screenshots
- No workflow needed — just URL and format

Site: Wikipedia (https://en.wikipedia.org)
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from maxun import Scrape, Config


async def main():
    scraper = Scrape(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "https://app.maxun.dev/"),
    ))

    robot = await scraper.create(
        "Wikipedia Web Scraping Article",
        "https://en.wikipedia.org/wiki/Web_scraping",
        formats=["markdown", "html", "screenshot-fullpage", "screenshot-visible"],
    )

    print(f"Robot created: {robot.id}")

    result = await robot.run()

    print("Result:", json.dumps(result, indent=2))

    data = result.get("data", {})
    print("\n=== Scraping Completed ===")
    print(f"Text length:       {len(data.get('text') or '')} characters")
    print(f"Markdown length:   {len(data.get('markdown') or '')} characters")
    print(f"HTML length:       {len(data.get('html') or '')} characters")
    print(f"Screenshots:       {len(result.get('screenshots') or [])}")

    text = data.get("text")
    if text:
        print(f"\nText preview (first 200 chars):\n{text[:200]}...")

    screenshots = result.get("screenshots") or []
    if screenshots:
        print("\nScreenshot URLs:")
        for i, screenshot in enumerate(screenshots, 1):
            url = screenshot if isinstance(screenshot, str) else screenshot.get("data")
            print(f"  {i}. {url}")


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
