from typing import Optional

from ._resource import Resource
from .builders.extract_builder import ExtractBuilder
from .llm_options import build_llm_payload
from .robot import Robot
from .types import LLMProvider


class Extract(Resource):
    """Pull structured data out of pages, either with CSS/XPath selectors
    (``create()``) or from a plain-English prompt (``from_prompt()``)."""

    robot_types = ("extract",)

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
