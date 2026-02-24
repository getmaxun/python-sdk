from typing import Optional
from .client import Client


class Robot:
    def __init__(self, client: Client, robot_data: dict):
        self.client = client
        self.robot_data = robot_data

    @property
    def id(self) -> str:
        return self.robot_data["recording_meta"]["id"]

    @property
    def name(self) -> str:
        return self.robot_data["recording_meta"]["name"]

    async def run(self, options: Optional[dict] = None):
        return await self.client.execute_robot(self.id, options or {})

    async def get_runs(self):
        return await self.client.get_runs(self.id)

    async def get_run(self, run_id: str):
        return await self.client.get_run(self.id, run_id)

    async def abort(self, run_id: str):
        await self.client.abort_run(self.id, run_id)

    async def delete(self):
        await self.client.delete_robot(self.id)

    async def refresh(self):
        self.robot_data = await self.client.get_robot(self.id)