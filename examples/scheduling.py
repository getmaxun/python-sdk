"""
Scheduling Example

This example demonstrates:
- Scheduling robots for periodic execution
- Different time intervals (minutes, hours, days, weeks, months)
- Setting timezone and time windows
- Updating and removing schedules

Site: Google Trends US (https://trends.google.com/trending?geo=US)
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from maxun import Extract, Config


async def main():
    extractor = Extract(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "https://app.maxun.dev/"),
    ))

    # Create a robot to track Google Trends
    robot = await (
        extractor
        .create("Google Trends (US)")
        .navigate("https://trends.google.com/trending?geo=US")
        .capture_list(
            {
                "selector": "tr.enOdEe-wZVHld-xMbwt.UlR2Yc",
                "maxItems": 20,
            }
        )
    )

    print(f"Robot created: {robot.id}")

    # Schedule: run every 6 hours
    await robot.schedule({
        "runEvery": 6,
        "runEveryUnit": "HOURS",
        "timezone": "America/New_York",
    })

    schedule = robot.get_schedule()
    print(f"\n✓ Scheduled: Every {schedule.get('runEvery')} {schedule.get('runEveryUnit')}")
    print(f"  Timezone: {schedule.get('timezone')}")
    print(f"  Next run: {schedule.get('nextRunAt')}")

    # Update schedule: business hours only (Mon–Fri, 9 AM – 5 PM)
    await robot.schedule({
        "runEvery": 2,
        "runEveryUnit": "HOURS",
        "timezone": "America/New_York",
        "startFrom": "MONDAY",
        "atTimeStart": "09:00",
        "atTimeEnd": "17:00",
    })

    schedule = robot.get_schedule()
    print(f"\n✓ Updated schedule: Every {schedule.get('runEvery')} {schedule.get('runEveryUnit')}")
    print(f"  Time window: {schedule.get('atTimeStart')} - {schedule.get('atTimeEnd')}")
    print(f"  Starting: {schedule.get('startFrom')}")

    # Run manually once to test
    print("\nRunning manually...")
    result = await robot.run()
    list_data = result.get("data", {}).get("listData") or []
    print(f"✓ Manual run completed: {len(list_data)} trends extracted")

    # Remove schedule
    await robot.unschedule()
    print("\n✓ Schedule removed")

    print("\n=== Other Scheduling Examples ===")
    print("Daily at midnight:")
    print('  {"runEvery": 1, "runEveryUnit": "DAYS", "timezone": "America/New_York", "atTimeStart": "00:00"}')
    print("\nWeekly on Fridays:")
    print('  {"runEvery": 1, "runEveryUnit": "WEEKS", "startFrom": "FRIDAY", "timezone": "America/New_York"}')
    print("\nMonthly on 1st:")
    print('  {"runEvery": 1, "runEveryUnit": "MONTHS", "dayOfMonth": 1, "timezone": "America/New_York"}')


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
