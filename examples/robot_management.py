"""
Robot Management Example

This example demonstrates:
- Listing all robots
- Getting a specific robot by ID
- Updating robot metadata
- Getting runs and execution history
- Deleting robots
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from maxun import Extract, Config


async def main():
    extractor = Extract(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "http://localhost:8080/api/sdk"),
    ))

    robot = await (
        extractor
        .create("Books Scraper")
        .navigate("https://books.toscrape.com/")
        .capture_list(
            {
                "selector": "article.product_pod",
                "maxItems": 10,
            }
        )
    )

    print(f"Robot created: {robot.id}")

    all_robots = await extractor.get_robots()
    print(f"\nTotal robots: {len(all_robots)}")

    fetched_robot = await extractor.get_robot(robot.id)
    print(f"Fetched robot: {fetched_robot.name}")

    await robot.update({"meta": {"name": "Updated Books Scraper"}})
    await robot.refresh()
    print(f"Updated name: {robot.name}")

    # Run the robot
    result = await robot.run()
    list_data = result.get("data", {}).get("listData") or []
    print(f"\nRun completed: {result.get('runId')}")
    print(f"Items extracted: {len(list_data)}")

    runs = await robot.get_runs()
    print(f"\nTotal runs: {len(runs)}")

    latest_run = await robot.get_latest_run()
    print(f"Latest run: {latest_run.get('runId') if latest_run else None}")

    specific_run = await robot.get_run(result.get("runId"))
    print(f"Specific run status: {specific_run.get('status')}")

    # Delete the robot
    await robot.delete()
    print("\nRobot deleted")


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
