import dataclasses
from .client import Client
from typing import List, Optional
from .types import Config, CrawlConfig, Format, LLMProvider
from .llm_options import build_llm_payload
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


class Crawl:
    def __init__(self, config: Config):
        self.client = Client(config)

    async def create(
        self,
        name: str,
        url: str,
        crawl_config: CrawlConfig,
        formats: Optional[List[Format]] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Robot:
        if not url:
            raise ValueError("URL is required")

        if not crawl_config:
            raise ValueError("Crawl configuration is required")

        robot_data = await self.client.create_crawl_robot(
            url,
            {
                "name": name,
                "crawlConfig": _dataclass_to_dict(crawl_config),
                **({"formats": formats} if formats else {}),
                **build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url),
            },
        )

        return Robot(self.client, robot_data)