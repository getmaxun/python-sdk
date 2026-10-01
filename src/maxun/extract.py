from typing import Any, Awaitable, Optional, Union

from ._naming import check_name, check_url, looks_like_url
from ._resource import Resource
from .builders.extract_builder import ExtractBuilder
from .llm_options import build_llm_payload
from .robot import Robot
from .types import LLMProvider


class Extract(Resource):
    """Pull structured data out of pages, either with CSS/XPath selectors
    (``create()``) or from a plain-English prompt (``from_prompt()``)."""

    robot_types = ("extract",)

    def __call__(
        self,
        name: str,
        url: Optional[str] = None,
        *args: Any,
        prompt: Optional[str] = None,
        monitor: Optional[bool] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Union[ExtractBuilder, Awaitable[Robot]]:
        """Create an extraction robot.

        With a ``prompt``, Maxun builds the robot from plain English (the URL is
        optional; without it Maxun searches for a suitable page)::

            robot = await maxun.extract("Products", "https://shop.example.com", prompt="Product names and prices")
            robot = await maxun.extract("YC companies", prompt="Company names from the YC directory")

        Without a prompt, returns a builder for a selector-based robot that
        starts on ``url``::

            robot = await maxun.extract("Products", "https://shop.example.com").capture_list({...}).build()

        :param name: Robot name, as shown in Maxun.
        :param monitor: Compare every run with the previous one.
        :param llm_*: With a prompt, self-hosted Maxun only.
        """
        call = "maxun.extract(name, url, ...)"
        if args:
            raise TypeError(f"{call} takes the settings as keyword arguments, e.g. prompt='...'.")
        if looks_like_url(name) and url is None:
            raise TypeError(f"{call} takes the robot name first, then the URL, e.g. maxun.extract('My robot', {name!r}).")
        name = check_name(name, call)
        llm = {
            "llm_provider": llm_provider, "llm_model": llm_model,
            "llm_api_key": llm_api_key, "llm_base_url": llm_base_url,
        }
        if prompt is not None:
            if url is not None:
                url = check_url(url, call)
            if not prompt.strip():
                raise ValueError("prompt is required")
            return self.from_prompt(prompt, url=url, name=name, monitor=monitor, **llm)

        if any(value is not None for value in llm.values()):
            raise TypeError("llm_* settings go with prompt=...; a selector robot does not use an LLM.")
        builder = self.create(name)
        builder.navigate(check_url(url, call, name))
        if monitor is not None:
            builder.monitor_changes(monitor)
        return builder

    def create(self, name: str) -> ExtractBuilder:
        """Start building a selector-based robot::

            robot = await (
                maxun.extract.create("Products")
                .navigate("https://example.com/shop")
                .capture_list({"selector": "article.product"})
                .build()
            )
        """
        builder = ExtractBuilder(name)
        builder.set_extractor(self)
        return builder

    async def build(self, builder: ExtractBuilder) -> Robot:
        """Save a builder as a robot. Same as ``await builder.build()``."""
        if not builder.workflow:
            raise ValueError("The robot has no steps. Call navigate(url) and a capture_* method first.")
        if not builder.meta.get("name"):
            raise ValueError("The robot needs a name: maxun.extract(name, url) or extract.create(name).")
        robot_data = await self.client.create_robot(builder.get_workflow())
        return Robot(self.client, robot_data)

    async def from_prompt(
        self,
        prompt: str,
        url: Optional[str] = None,
        name: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        monitor: Optional[bool] = None,
    ) -> Robot:
        """Create an extraction robot from a natural-language prompt.

        :param url: Page to extract from. If left out, Maxun searches the web
            for a suitable page based on the prompt.
        :param llm_*: Self-hosted Maxun only (where they are required). Maxun
            Cloud manages the model and rejects these, so leave them unset there.
        """
        if not prompt or not prompt.strip():
            raise ValueError("prompt is required")
        options = {
            "prompt": prompt.strip(),
            "url": url,
            "robotName": name,
            "monitor": monitor,
            **build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url),
        }
        result = await self.client.extract_with_llm(options)
        return Robot(self.client, await self.client.get_robot(result["robotId"]))

    async def extract(
        self,
        prompt: str,
        url: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        robot_name: Optional[str] = None,
        monitor: Optional[bool] = None,
    ) -> Robot:
        """Older name for :meth:`from_prompt`."""
        return await self.from_prompt(
            prompt, url=url, name=robot_name, llm_provider=llm_provider, llm_model=llm_model,
            llm_api_key=llm_api_key, llm_base_url=llm_base_url, monitor=monitor,
        )
