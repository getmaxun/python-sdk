import time
import random
import string
from typing import List, Optional

from .client import Client
from .types import Config, LLMProvider
from .robot import Robot
from .builders.extract_builder import ExtractBuilder


class Extract:
    def __init__(self, config: Config):
        self.client = Client(config)

    def create(self, name: str) -> ExtractBuilder:
        builder = ExtractBuilder(name)
        builder.set_extractor(self)
        return builder

    async def build(self, builder: ExtractBuilder) -> Robot:
        workflow = builder.get_workflow_array()
        meta = builder.get_meta()

        robot_id = f"robot_{int(time.time() * 1000)}_{self._random_string()}"
        meta["id"] = robot_id

        workflow_file = {
            "meta": meta,
            "workflow": workflow,
        }

        robot_data = await self.client.create_robot(workflow_file)
        return Robot(self.client, robot_data)

    async def get_robots(self) -> List[Robot]:
        robots = await self.client.get_robots()
        extract_robots = [
            r for r in robots if r["recording_meta"]["robotType"] == "extract"
        ]
        return [Robot(self.client, r) for r in extract_robots]

    async def get_robot(self, robot_id: str) -> Robot:
        robot = await self.client.get_robot(robot_id)
        return Robot(self.client, robot)

    async def delete_robot(self, robot_id: str) -> None:
        await self.client.delete_robot(robot_id)

    async def extract(
        self,
        prompt: str,
        url: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        robot_name: Optional[str] = None,
    ) -> Robot:
        options = {
            "prompt": prompt,
            "url": url,
            "llmProvider": llm_provider,
            "llmModel": llm_model,
            "llmApiKey": llm_api_key,
            "llmBaseUrl": llm_base_url,
            "robotName": robot_name,
        }
        robot_data = await self.client.extract_with_llm(options)
        robot = await self.client.get_robot(robot_data["robotId"])
        return Robot(self.client, robot)

    def _random_string(self, length: int = 9) -> str:
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
