from typing import Any, List, Optional

from ._naming import check_name, check_no_extra, check_url
from ._resource import Resource
from .llm_options import build_llm_payload
from .robot import Robot
from .types import Format, LLMProvider

SCRAPE_FORMATS = ("markdown", "html", "text", "links", "summary", "screenshot-visible", "screenshot-fullpage")


def check_formats(formats: Optional[List[str]], allowed=SCRAPE_FORMATS) -> Optional[List[str]]:
    if formats is None:
        return None
    if isinstance(formats, str):
        formats = [formats]
    invalid = [f for f in formats if f not in allowed]
    if invalid:
        raise ValueError(f"Invalid formats: {', '.join(map(str, invalid))}. Use any of: {', '.join(allowed)}.")
    return list(formats)


class Scrape(Resource):
    """Turn a single page into Markdown, HTML, text, links, a summary or screenshots."""

    robot_types = ("scrape",)

    async def create(
        self,
        name: str,
        url: str,
        formats: Optional[List[Format]] = None,
        smart_queries: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        monitor: Optional[bool] = None,
    ) -> Robot:
        """Create a scrape robot. Run it with ``await robot.run()``.

        :param name: Robot name. Creating again with the same name and settings
            returns the existing robot; different settings raise ConflictError.
        :param url: Page to scrape.
        :param formats: Any of markdown, html, text, links, summary,
            screenshot-visible, screenshot-fullpage. Defaults to ["markdown"].
        :param smart_queries: A question the LLM answers about the page on every
            run; read the answer from ``result.smart_query_result``.
        :param llm_*: Self-hosted Maxun only, needed for ``summary`` and
            ``smart_queries``. Leave unset on Maxun Cloud.
        :param monitor: Compare every run with the previous one.
        """
        if not url:
            raise ValueError("url is required")

        meta: dict = {
            "name": name,
            "type": "scrape",
            "url": url,
            "formats": check_formats(formats) or ["markdown"],
        }
        if smart_queries and smart_queries.strip():
            meta["promptInstructions"] = smart_queries.strip()
        if monitor is not None:
            meta["monitor"] = monitor
        meta.update(build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url))

        robot_data = await self.client.create_robot({"meta": meta, "workflow": []})
        return Robot(self.client, robot_data)

    async def __call__(
        self,
        name: str,
        url: Optional[str] = None,
        *args: Any,
        formats: Optional[List[Format]] = None,
        smart_queries: Optional[str] = None,
        monitor: Optional[bool] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Robot:
        """Create a scrape robot::

            robot = await maxun.scrape("Maxun home", "https://maxun.dev", formats=["markdown", "html"])

        :param name: Robot name, as shown in Maxun.
        :param url: Page to scrape.
        :param formats: Any of markdown, html, text, links, summary,
            screenshot-visible, screenshot-fullpage. Defaults to ["markdown"].
        :param smart_queries: A question the LLM answers about the page on every run.
        :param monitor: Compare every run with the previous one.
        :param llm_*: Self-hosted Maxun only, needed for ``summary`` and Smart Queries.
        """
        call = "maxun.scrape(name, url, ...)"
        check_no_extra(args, call)
        url = check_url(url, call, name)
        name = check_name(name, call)
        check_formats(formats)
        return await self.create(
            name, url, formats=formats, smart_queries=smart_queries, llm_provider=llm_provider,
            llm_model=llm_model, llm_api_key=llm_api_key, llm_base_url=llm_base_url, monitor=monitor,
        )
