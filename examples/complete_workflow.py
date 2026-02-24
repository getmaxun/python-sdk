"""
Complete Workflow Example

Demonstrates a real-world use case combining multiple features:
- Data extraction with pagination
- Scheduling
- Webhooks
- Execution history
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from maxun import Extract, Config


async def main():
    print("=== Complete Workflow Example ===\n")

    extractor = Extract(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "http://localhost:8080/api/sdk"),
    ))

    print("Creating full extraction robot...")
    robot = await (
        extractor
        .create("Trending Books Daily")
        .navigate("https://openlibrary.org/trending/daily")
        .capture_list(
            {
                "selector": "li.searchResultItem.sri--w-main",
                "pagination": {
                    "type": "clickNext",
                    "selector": 'a[data-ol-link-track="Pager|Next"]',
                },
                "maxItems": 25,
            }
        )
    )

    print(f"✓ Robot created: {robot.id}\n")

    print("Setting up webhook for notifications...")
    await robot.add_webhook({
        "url": "https://your-webhook-endpoint.com/notifications",
        "events": ["run.completed", "run.failed"],
    })
    print("✓ Webhook configured\n")

    print("Scheduling robot to run every day...")
    await robot.schedule({
        "runEvery": 1,
        "runEveryUnit": "DAYS",
        "timezone": "UTC",
    })
    print("✓ Robot scheduled\n")

    print("Robot Configuration Summary:")
    print(f"  Name: {robot.name}")
    print(f"  ID:   {robot.id}")

    schedule = robot.get_schedule()
    print(f"  Schedule: Every {schedule.get('runEvery')} {schedule.get('runEveryUnit')}")

    webhooks = robot.get_webhooks()
    print(f"  Webhooks: {len(webhooks or [])} configured\n")

    print("Fetching execution history...")
    runs = await robot.get_runs()
    print(f"✓ Found {len(runs)} runs:")
    for i, run in enumerate(runs[:5], 1):
        print(f"  {i}. {run.get('runId')} - {run.get('status')} - {run.get('startedAt')}")


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
