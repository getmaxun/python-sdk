from typing import Any, Dict, List, Optional, Union

from ._naming import check_name, check_no_extra, check_url
from ._resource import Resource
from ._utils import to_payload
from .llm_options import build_llm_payload
from .robot import Robot
from .scrape import check_formats
from .types import CrawlConfig, CrawlMode, Format, LLMProvider


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

    async def __call__(
        self,
        name: str,
        url: Optional[str] = None,
        *args: Any,
        mode: CrawlMode = "domain",
        limit: int = 50,
        max_depth: int = 3,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        use_sitemap: bool = True,
        follow_links: bool = True,
        respect_robots: bool = True,
        formats: Optional[List[Format]] = None,
        monitor: Optional[bool] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Robot:
        """Create a crawl robot::

            robot = await maxun.crawl("Docs", "https://docs.example.com", limit=20, formats=["markdown"])

        :param name: Robot name, as shown in Maxun.
        :param url: Where the crawl starts.
        :param mode: Stay on the same ``"domain"``, ``"subdomain"`` or URL ``"path"``.
        :param limit: Maximum number of pages.
        :param max_depth: How many links deep to follow.
        :param include_paths: URL patterns to keep, e.g. ``["/blog/*"]``.
        :param exclude_paths: URL patterns to skip.
        :param formats: What to capture from each page. Defaults to ["markdown"].
        :param monitor: Compare every run with the previous one.
        :param llm_*: Self-hosted Maxun only, needed for the ``summary`` format.
        """
        call = "maxun.crawl(name, url, ...)"
        check_no_extra(args, call)
        url = check_url(url, call, name)
        name = check_name(name, call)
        check_formats(formats)
        config = CrawlConfig(
            mode=mode, limit=limit, max_depth=max_depth, include_paths=include_paths,
            exclude_paths=exclude_paths, use_sitemap=use_sitemap, follow_links=follow_links,
            respect_robots=respect_robots,
        )
        return await self.create(
            name, url, config, formats=formats, llm_provider=llm_provider, llm_model=llm_model,
            llm_api_key=llm_api_key, llm_base_url=llm_base_url, monitor=monitor,
        )
