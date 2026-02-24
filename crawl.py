from typing import Any
from .client import Client
from .types import Config, CrawlConfig
from .robot import Robot


class Crawl:
    def __init__(self, config: Config):
        self.client = Client(config)

    async def create(self, name: str, url: str, crawl_config: CrawlConfig) -> Robot:
        if not url:
            raise ValueError("URL is required")

        if not crawl_config:
            raise ValueError("Crawl configuration is required")

        robot_data = await self.client.create_crawl_robot(
            url,
            {
                "name": name,
                "crawlConfig": crawl_config,
            },
        )

        return Robot(self.client, robot_data)