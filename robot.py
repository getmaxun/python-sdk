from typing import Optional, List
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

    def get_data(self) -> dict:
        return self.robot_data

    async def run(self, options: Optional[dict] = None):
        return await self.client.execute_robot(self.id, options)

    async def get_runs(self) -> list:
        return await self.client.get_runs(self.id)

    async def get_run(self, run_id: str) -> dict:
        return await self.client.get_run(self.id, run_id)

    async def get_latest_run(self) -> Optional[dict]:
        runs = await self.get_runs()
        if not runs:
            return None
        return sorted(runs, key=lambda r: r.get("startedAt", ""), reverse=True)[0]

    async def abort(self, run_id: str) -> None:
        await self.client.abort_run(self.id, run_id)

    async def schedule(self, config: dict) -> None:
        updated = await self.client.schedule_robot(self.id, config)
        self.robot_data = updated

    async def unschedule(self) -> None:
        updated = await self.client.unschedule_robot(self.id)
        self.robot_data = updated

    async def add_webhook(self, webhook: dict) -> None:
        updated = await self.client.add_webhook(self.id, webhook)
        self.robot_data = updated

    def get_webhooks(self) -> Optional[list]:
        return self.robot_data.get("webhooks") or None

    async def remove_webhooks(self) -> None:
        updated = await self.client.update_robot(self.id, {"webhooks": None})
        self.robot_data = updated

    def get_schedule(self) -> Optional[dict]:
        return self.robot_data.get("schedule") or None

    async def update(self, updates: dict) -> None:
        updated = await self.client.update_robot(self.id, updates)
        self.robot_data = updated

    async def delete(self) -> None:
        await self.client.delete_robot(self.id)

    async def refresh(self) -> None:
        self.robot_data = await self.client.get_robot(self.id)
