from typing import Any, Dict, List, Optional, Union

from ._naming import check_name, check_no_extra
from ._resource import Resource
from ._utils import to_payload, warn
from .llm_options import build_llm_payload
from .robot import Robot
from .scrape import check_formats
from .types import Format, LLMProvider, SearchConfig, SearchMode, SearchTimeRange


class Search(Resource):
    """Search the web (DuckDuckGo) and optionally scrape every result."""

    robot_types = ("search",)

    async def create(
        self,
        name: str,
        search_config: Union[SearchConfig, Dict[str, Any], str],
        formats: Optional[List[Format]] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Robot:
        """Create a search robot. Run it with ``await robot.run()`` and read
        ``result.search_data``.

        :param search_config: A :class:`SearchConfig`, a dict, or just the query
            string. ``mode="discover"`` returns titles/URLs/snippets only;
            ``mode="scrape"`` (default) also scrapes each result.
        :param formats: What to capture from each result in scrape mode.
            Defaults to ["markdown"].
        :param llm_*: Self-hosted Maxun only, needed for the ``summary`` format.
        """
        if isinstance(search_config, str):
            search_config = SearchConfig(query=search_config)
        if not search_config:
            raise ValueError("search_config is required")

        defaults = to_payload(SearchConfig(query=""))
        payload = {**defaults, **to_payload(search_config)}
        if not payload.get("query"):
            raise ValueError("A search query is required")
        if payload.get("mode") not in ("discover", "scrape"):
            raise ValueError('mode must be "discover" or "scrape"')

        time_range = payload.pop("timeRange", None)
        if time_range:
            payload["filters"] = {**(payload.get("filters") or {}), "timeRange": time_range}

        if formats and payload["mode"] == "discover":
            warn('formats only apply in mode="scrape"; a discover search returns result links only.')

        robot_data = await self.client.create_search_robot(
            {
                "name": name,
                "searchConfig": payload,
                **({"formats": check_formats(formats)} if formats else {}),
                **build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url),
            }
        )
        return Robot(self.client, robot_data)

    async def __call__(
        self,
        name: str,
        query: Optional[str] = None,
        *args: Any,
        mode: SearchMode = "scrape",
        limit: int = 10,
        time_range: Optional[SearchTimeRange] = None,
        formats: Optional[List[Format]] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Robot:
        """Create a search robot::

            robot = await maxun.search("AI news", "AI model releases", mode="discover", time_range="week")

        :param name: Robot name, as shown in Maxun.
        :param query: What to search for.
        :param mode: ``"discover"`` returns titles, URLs and snippets;
            ``"scrape"`` (default) also scrapes every result.
        :param limit: Number of results.
        :param time_range: ``"day"``, ``"week"``, ``"month"`` or ``"year"``.
        :param formats: What to capture from each result in scrape mode. Defaults to ["markdown"].
        :param llm_*: Self-hosted Maxun only, needed for the ``summary`` format.
        """
        call = "maxun.search(name, query, ...)"
        check_no_extra(args, call)
        name = check_name(name, call)
        if not isinstance(query, str) or not query.strip():
            raise ValueError("maxun.search(name, query, ...) needs a search query, e.g. maxun.search('AI news', 'AI model releases').")
        config = SearchConfig(query=query.strip(), mode=mode, limit=limit, time_range=time_range)
        return await self.create(
            name, config, formats=formats, llm_provider=llm_provider, llm_model=llm_model,
            llm_api_key=llm_api_key, llm_base_url=llm_base_url,
        )
