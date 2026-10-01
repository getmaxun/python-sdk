from typing import Any, List, Optional

from ._naming import auto_name, check_url, describe_url
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
        url: str,
        *args: Any,
        name: Optional[str] = None,
        formats: Optional[List[Format]] = None,
        smart_queries: Optional[str] = None,
        monitor: Optional[bool] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Robot:
        """Create a scrape robot::

            robot = await maxun.scrape("https://maxun.dev", formats=["markdown", "html"])

        :param formats: Any of markdown, html, text, links, summary,
            screenshot-visible, screenshot-fullpage. Defaults to ["markdown"].
        :param smart_queries: A question the LLM answers about the page on every run.
        :param monitor: Compare every run with the previous one.
        :param name: Robot name. Defaults to one made from the URL and settings,
            so the same call returns the same robot.
        :param llm_*: Self-hosted Maxun only, needed for ``summary`` and Smart Queries.
        """
        if args:
            raise TypeError(
                "maxun.scrape(url, ...) takes the URL first and the settings as keyword arguments. "
                "Pass the robot name as name=..."
            )
        url = check_url(url, "maxun.scrape(url, ...)")
        settings = {
            "type": "scrape",
            "url": url,
            "formats": check_formats(formats) or ["markdown"],
            "smartQueries": smart_queries.strip() if smart_queries and smart_queries.strip() else None,
            "monitor": monitor,
            **build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url),
        }
        return await self._create_reusing(
            name,
            auto_name("Scrape", describe_url(url), settings),
            lambda robot_name: self.create(
                robot_name, url, formats=formats, smart_queries=smart_queries, llm_provider=llm_provider,
                llm_model=llm_model, llm_api_key=llm_api_key, llm_base_url=llm_base_url, monitor=monitor,
            ),
        )
