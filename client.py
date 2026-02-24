import httpx
from typing import Any, Dict, Optional
from .types import Config, MaxunError


class Client:
    def __init__(self, config: Config):
        self.api_key = config.api_key

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        if config.team_id:
            headers["x-team-id"] = config.team_id

        self.base_url = config.base_url or "http://localhost:8080/api/sdk"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0,
        )

    async def _handle(self, request):
        try:
            response = await request
            response.raise_for_status()
            data = response.json()
            return data.get("data")
        except httpx.HTTPStatusError as e:
            try:
                payload = e.response.json()
            except Exception:
                payload = None
            raise MaxunError(
                payload.get("error") if payload else str(e),
                status_code=e.response.status_code,
                details=payload,
            )
        except httpx.RequestError as e:
            raise MaxunError("No response from server", details=str(e))

    async def get_robots(self):
        return await self._handle(self.client.get("/robots"))

    async def get_robot(self, robot_id: str):
        data = await self._handle(self.client.get(f"/robots/{robot_id}"))
        if not data:
            raise MaxunError(f"Robot {robot_id} not found", 404)
        return data

    async def create_robot(self, workflow_file: dict):
        return await self._handle(
            self.client.post("/robots", json=workflow_file, timeout=120)
        )

    async def update_robot(self, robot_id: str, updates: dict):
        return await self._handle(
            self.client.put(f"/robots/{robot_id}", json=updates)
        )

    async def delete_robot(self, robot_id: str):
        await self._handle(self.client.delete(f"/robots/{robot_id}"))

    async def execute_robot(self, robot_id: str, options: Optional[dict] = None):
        return await self._handle(
            self.client.post(
                f"/robots/{robot_id}/execute",
                json={
                    "params": options.get("params") if options else None,
                    "webhook": options.get("webhook") if options else None,
                },
                timeout=options.get("timeout", 300) if options else 300,
            )
        )

    async def get_runs(self, robot_id: str):
        return await self._handle(self.client.get(f"/robots/{robot_id}/runs"))

    async def get_run(self, robot_id: str, run_id: str):
        return await self._handle(
            self.client.get(f"/robots/{robot_id}/runs/{run_id}")
        )

    async def abort_run(self, robot_id: str, run_id: str):
        await self._handle(
            self.client.post(f"/robots/{robot_id}/runs/{run_id}/abort")
        )

    async def extract_with_llm(self, options: dict):
        return await self._handle(
            self.client.post("/extract/llm", json=options, timeout=300)
        )

    async def create_crawl_robot(self, url: str, options: dict):
        return await self._handle(
            self.client.post("/crawl", json={"url": url, **options})
        )

    async def create_search_robot(self, options: dict):
        return await self._handle(
            self.client.post("/search", json=options)
        )