"""Capture a repeated element as a list, across pages.

Fields inside each item are detected automatically. Leave out "pagination" to
let Maxun detect it, or set it yourself:
  {"type": "scrollDown"}                                   infinite scroll
  {"type": "clickNext", "selector": "a.next"}              "Next" button
  {"type": "clickLoadMore", "selector": "button.more"}     "Load more" button
  {"type": "none"}                                         first page only
"""
import asyncio
import json

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await (
            maxun.extract.create("Open Library Trending")
            .navigate("https://openlibrary.org/trending/daily")
            .capture_list({
                "selector": "li.searchResultItem",
                "pagination": {"type": "clickNext", "selector": 'a[data-ol-link-track="Pager|Next"]'},
                "max_items": 40,
            })
            .build()
        )
        result = await robot.run()
        print(f"{len(result.list_data)} books")
        print(json.dumps(result.list_data[:3], indent=2))

        # Change how many items are collected without rebuilding the robot.
        await robot.set_list_limit(10)


asyncio.run(main())
