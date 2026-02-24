"""
Webhooks Example

This example demonstrates:
- Adding webhooks for robot events
- Configuring webhook events and headers
- Getting webhook notifications when runs complete

Site: Indie Hackers (https://www.indiehackers.com)
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

    # Create a robot to extract Indie Hackers posts
    robot = await (
        extractor
        .create("Indie Hackers Posts Monitor")
        .navigate("https://www.indiehackers.com/tags/artificial-intelligence")
        .capture_list(
            {
                "selector": "a.ember-view.portal-entry",
                "maxItems": 10,
            }
        )
    )

    print(f"Robot created: {robot.id}")

    # Add webhook for notifications
    await robot.add_webhook({
        "url": "https://your-webhook-url.com/notifications",
        "events": ["run.completed", "run.failed"],
        "headers": {
            "Authorization": "Bearer your-secret-token",
            "X-Custom-Header": "maxun-webhook",
        },
    })

    print("\n✓ Webhook added")
    print("  URL: https://your-webhook-url.com/notifications")
    print("  Events: run.completed, run.failed")

    webhooks = robot.get_webhooks()
    print(f"\n✓ Total webhooks configured: {len(webhooks or [])}")

    # Run the robot — webhook will be triggered on completion
    print("\nRunning robot...")
    result = await robot.run()

    list_data = result.get("data", {}).get("listData") or []
    print(f"\n✓ Run completed: {result.get('runId')}")
    print(f"  Status: {result.get('status')}")
    print(f"  Items extracted: {len(list_data)}")
    print("\n→ Webhook notification has been sent to your endpoint")


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
