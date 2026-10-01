from typing import Any, Awaitable, Optional, Union

from ._naming import auto_name, check_url, describe_url, shorten
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
        *args: Any,
        prompt: Optional[str] = None,
        name: Optional[str] = None,
        monitor: Optional[bool] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        **unexpected: Any,
    ) -> Union[ExtractBuilder, Awaitable[Robot]]:
        """Create an extraction robot.

        With a ``prompt``, Maxun builds the robot from plain English (the URL is
        optional; without it Maxun searches for a suitable page)::

            robot = await maxun.extract("https://shop.example.com", prompt="Product names and prices")

        Without a prompt, returns a builder for a selector-based robot that
        starts on ``url``::

            robot = await maxun.extract("https://shop.example.com").capture_list({...}).build()

        :param name: Robot name. Defaults to one made from the URL and settings.
        :param monitor: Compare every run with the previous one.
        :param llm_*: With a prompt, self-hosted Maxun only.
        """
        # Signature: maxun.extract(url=None, *, prompt=None, name=None, monitor=None, llm_*=None)
        keyword_url = unexpected.pop("url", None)
        if unexpected:
            raise TypeError(f"maxun.extract() got unexpected arguments: {', '.join(unexpected)}")
        if len(args) > 1 or (args and keyword_url is not None):
            raise TypeError(
                "maxun.extract(url, prompt=...) takes the URL first and the settings as keyword "
                "arguments. Pass the robot name as name=..."
            )
        url: Optional[str] = args[0] if args else keyword_url
        llm = {
            "llm_provider": llm_provider, "llm_model": llm_model,
            "llm_api_key": llm_api_key, "llm_base_url": llm_base_url,
        }
        if prompt is not None:
            if url is not None:
                url = check_url(url, "maxun.extract(url, prompt=...)")
            if not prompt.strip():
                raise ValueError("prompt is required")
            settings = {
                "type": "extract",
                "prompt": prompt.strip(),
                "url": url,
                "monitor": monitor,
                **build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url),
            }
            subject = describe_url(url) if url else shorten(prompt)
            return self._create_reusing(
                name,
                auto_name("Extract", subject, settings),
                lambda robot_name: self.from_prompt(prompt, url=url, name=robot_name, monitor=monitor, **llm),
            )

        if any(value is not None for value in llm.values()):
            raise TypeError("llm_* settings go with prompt=...; a selector robot does not use an LLM.")
        if url is None:
            raise TypeError(
                'maxun.extract() needs a URL to start on, e.g. maxun.extract("https://example.com"), '
                "or prompt=... to describe the data."
            )
        builder = ExtractBuilder(name)
        builder.set_extractor(self)
        builder.navigate(check_url(url, "maxun.extract(url)"))
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
            workflow = builder.get_workflow()
            settings = {"meta": {k: v for k, v in workflow["meta"].items() if k != "name"}, "workflow": workflow["workflow"]}
            builder.name = builder.meta["name"] = auto_name("Extract", describe_url(builder.start_url or ""), settings)
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
