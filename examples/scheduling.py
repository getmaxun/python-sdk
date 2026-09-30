"""Run a robot automatically on a schedule.

run_every_unit is MINUTES, HOURS, DAYS, WEEKS or MONTHS.
at_time_start ("HH:MM") sets the time of day for DAYS/WEEKS/MONTHS;
start_from sets the weekday for WEEKS; day_of_month sets the day for MONTHS.
"""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun, ScheduleConfig

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.scrape("Example Daily", "https://example.com")

        # Every 6 hours
        schedule = await robot.schedule(run_every=6, run_every_unit="HOURS", timezone="Asia/Kolkata")
        print("Next run:", schedule.get("nextRunAt"))

        # Every Monday at 09:00
        await robot.schedule(ScheduleConfig(
            run_every=1, run_every_unit="WEEKS", timezone="Asia/Kolkata",
            start_from="MONDAY", at_time_start="09:00",
        ))
        print(robot.get_schedule())

        # On the 1st of every month at 06:30
        await robot.schedule(run_every=1, run_every_unit="MONTHS", day_of_month=1, at_time_start="06:30")

        await robot.unschedule()


asyncio.run(main())
