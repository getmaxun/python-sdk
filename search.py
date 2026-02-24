from .client import Client
from .types import Config, SearchConfig
from .robot import Robot


class Search:
    def __init__(self, config: Config):
        self.client = Client(config)

    async def create(self, name: str, search_config: SearchConfig) -> Robot:
        if not search_config:
            raise ValueError("Search configuration is required")

        if not search_config.query:
            raise ValueError("Search query is required")

        robot_data = await self.client.create_search_robot(
            {
                "name": name,
                "searchConfig": search_config,
            }
        )

        return Robot(self.client, robot_data)