from typing import Any, Dict, List, Optional, Union

from ._resource import Resource
from ._utils import to_payload
from .llm_options import build_llm_payload
from .robot import Robot
from .scrape import check_formats
from .types import CrawlConfig, Format, LLMProvider


class Crawl(Resource):
    """Visit many pages of a site, starting from one URL, and scrape each one."""

    robot_types = ("crawl",)

    async def create(
        self,
        name: str,
        url: str,
        crawl_config: Optional[Union[CrawlConfig, Dict[str, Any]]] = None,
        formats: Optional[List[Format]] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        monitor: Optional[bool] = None,
    ) -> Robot:
        """Create a crawl robot. Run it with ``await robot.run()`` and read
        ``result.crawl_data`` (one entry per page).

        :param crawl_config: A :class:`CrawlConfig` or dict. Defaults to the same
            domain, up to 50 pages, 3 links deep, using the sitemap.
        :param formats: What to capture from each page. Defaults to ["markdown"].
        :param llm_*: Self-hosted Maxun only, needed for the ``summary`` format.
        :param monitor: Compare every run with the previous one.
        """
        if not url:
            raise ValueError("url is required")

        config = crawl_config if crawl_config is not None else CrawlConfig()
        if isinstance(config, dict):
            # Fill in the same defaults as CrawlConfig so a partial dict still crawls.
            config = {**to_payload(CrawlConfig()), **to_payload(config)}
        payload = to_payload(config)

        robot_data = await self.client.create_crawl_robot(
            url,
            {
                "name": name,
                "crawlConfig": payload,
                **({"formats": check_formats(formats)} if formats else {}),
                **build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url),
            },
        )
        return await self._after_create(robot_data, monitor)

    #: ``await maxun.crawl(name, url, ...)`` is the same as ``create``.
    __call__ = create
