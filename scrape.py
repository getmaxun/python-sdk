import time
import random
import string
from typing import List, Optional

from .client import Client
from .types import Config, WorkflowFile, Format
from .robot import Robot


class ScrapeOptions:
    def __init__(self, formats: Optional[List[Format]] = None):
        self.formats = formats or ["markdown"]


class Scrape:
    def __init__(self, config: Config):
        self.client = Client(config)

    async def create(
        self,
        name: str,
        url: str,
        options: Optional[ScrapeOptions] = None,
    ) -> Robot:
        if not url:
            raise ValueError("URL is required")

        options = options or ScrapeOptions()

        robot_id = f"robot_{int(time.time() * 1000)}_{self._random_string()}"

        workflow_file: WorkflowFile = {
            "meta": {
                "name": name,
                "id": robot_id,
                "robotType": "scrape",
                "url": url,
                "formats": options.formats,
            },
            "workflow": [],
        }

        robot_data = await self.client.create_robot(workflow_file)
        return Robot(self.client, robot_data)

    def _random_string(self, length: int = 9) -> str:
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))