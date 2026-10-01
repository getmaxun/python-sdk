"""The same SDK without async/await, for scripts and notebooks."""
from dotenv import load_dotenv
from maxun import MaxunSync

load_dotenv()

with MaxunSync() as maxun:
    robot = maxun.scrape("Example (sync)", "https://example.com")
    print(robot.run().markdown)

    robot = (
        maxun.extract("HN Titles (sync)", "https://news.ycombinator.com")
        .capture_list({"selector": "tr.athing", "max_items": 10})
        .build()
    )
    print(robot.run().list_data[:3])
