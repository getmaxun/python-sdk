"""The same SDK without async/await, for scripts and notebooks."""
from dotenv import load_dotenv
from maxun import MaxunSync

load_dotenv()

with MaxunSync() as maxun:
    robot = maxun.scrape.create("Example (sync)", "https://example.com")
    print(robot.run().markdown)

    robot = (
        maxun.extract.create("HN titles (sync)")
        .navigate("https://news.ycombinator.com")
        .capture_list({"selector": "tr.athing", "max_items": 10})
        .build()
    )
    print(robot.run().list_data[:3])
