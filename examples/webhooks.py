"""Get notified when a run finishes.

Maxun POSTs {"event_type": "run_completed" | "run_failed", "timestamp", "webhook_id", "data"}
to your URL. Failed deliveries are retried with exponential backoff.
"""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun, WebhookConfig

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.scrape.create("Example With Webhook", "https://example.com")

        # Both events by default
        hook = await robot.add_webhook("https://your-server.example/maxun-hook")
        print("Added", hook["id"], hook["events"])

        # Only failures, with more retries
        await robot.add_webhook(WebhookConfig(
            url="https://alerts.example/maxun-failed",
            events=["run_failed"],
            retry_attempts=5,
        ))

        print([w["url"] for w in robot.get_webhooks()])

        await robot.remove_webhook("https://alerts.example/maxun-failed")
        await robot.remove_webhooks()  # remove all


asyncio.run(main())
