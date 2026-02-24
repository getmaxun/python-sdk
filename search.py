import dataclasses
from .client import Client
from .types import Config, SearchConfig
from .robot import Robot

def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _dataclass_to_dict(obj) -> dict:
    """Convert a dataclass to a camelCase dict, dropping None values."""
    return {
        _to_camel(k): v
        for k, v in dataclasses.asdict(obj).items()
        if v is not None
    }

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
                "searchConfig": _dataclass_to_dict(search_config),
            }
        )

        return Robot(self.client, robot_data)