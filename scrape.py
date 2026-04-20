import time
import random
import string
from typing import List, Optional

from .client import Client
from .types import Config, WorkflowFile, Format
from .robot import Robot

class Scrape:
    def __init__(self, config: Config):
        self.client = Client(config)

    async def create(
        self,
        name: str,
        url: str,
        formats: Optional[List[Format]] = None,
        smart_queries: Optional[str] = None,
    ) -> Robot:
        """
        Create a scrape robot.

        :param name: Robot name.
        :param url: URL to scrape.
        :param formats: Output formats (default: ["markdown"]).
        :param smart_queries: Optional Smart Queries prompt. After scraping the
            LLM analyzes the page and returns an answer.
        """
        if not url:
            raise ValueError("URL is required")

        robot_id = f"robot_{int(time.time() * 1000)}_{self._random_string()}"

        meta: dict = {
            "name": name,
            "id": robot_id,
            "robotType": "scrape",
            "url": url,
            "formats": formats or ["markdown"],
        }
        if smart_queries:
            meta["smartQueries"] = smart_queries.strip()

        workflow_file: WorkflowFile = {
            "meta": meta,
            "workflow": [],
        }

        robot_data = await self.client.create_robot(workflow_file)
        return Robot(self.client, robot_data)

    def _random_string(self, length: int = 9) -> str:
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))