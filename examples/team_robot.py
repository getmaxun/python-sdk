"""
Team Robot Example

This example demonstrates:
- Creating a robot scoped to a team (using team_id in Config)
- Running the robot in team space
- Listing runs scoped to the team
- Deleting the robot from the team

Prerequisites:
- MAXUN_API_KEY: API key of a user who is a member of the team
- MAXUN_TEAM_ID: The UUID of the team (visible in team settings)
- MAXUN_BASE_URL: Base URL of your Maxun instance
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from maxun import Extract, Config


async def main():
    extractor = Extract(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "https://app.maxun.dev/api/sdk/"),
        team_id=os.environ.get("MAXUN_TEAM_ID"),
    ))

    print(f"Creating robot in team: {os.environ.get('MAXUN_TEAM_ID')}")

    robot = await (
        extractor
        .create("Team Books Scraper")
        .navigate("https://books.toscrape.com/")
        .capture_list({
            "selector": "article.product_pod",
            "maxItems": 5,
        })
    )

    print(f"Robot created: {robot.id}")
    print(f"Robot name:   {robot.name}")

    team_robots = await extractor.get_robots()
    print(f"\nTotal robots in team: {len(team_robots)}")

    print("\nRunning robot...")
    result = await robot.run()

    list_data = result.get("data", {}).get("listData") or []
    print("\n=== Run Completed ===")
    print(f"Status: {result.get('status')}")
    print(f"Run ID: {result.get('runId')}")
    print(f"Items extracted: {len(list_data)}")

    runs = await robot.get_runs()
    print(f"\nTotal runs for this robot in team: {len(runs)}")

    specific_run = await robot.get_run(result.get("runId"))
    print(f"Fetched run status: {specific_run.get('status')}")


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
