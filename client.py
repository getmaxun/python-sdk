import time
import os
import httpx
from datetime import datetime, timezone
from typing import Optional, Union
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

        self.base_url = config.base_url or "https://app.maxun.dev/api/sdk/"

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
                (payload.get("error") or payload.get("message")) if payload else str(e),
                status_code=e.response.status_code,
                details=payload,
            )
        except httpx.RequestError as e:
            raise MaxunError("No response from server", details=str(e))

    async def get_robots(self):
        data = await self._handle(self.client.get("/robots"))
        return data or []

    async def get_robot(self, robot_id: str):
        data = await self._handle(self.client.get(f"/robots/{robot_id}"))
        if not data:
            raise MaxunError(f"Robot {robot_id} not found", 404)
        return data

    async def create_robot(self, workflow_file: dict):
        # Normalize both `type` and `robotType` in meta, mirroring the Node SDK behaviour
        meta = workflow_file.get("meta") or {}
        robot_type_value = meta.get("robotType") or meta.get("type")
        payload = {
            **workflow_file,
            "meta": {
                **meta,
                "type": robot_type_value,
                "robotType": robot_type_value,
            },
        }
        data = await self._handle(
            self.client.post("/robots", json=payload, timeout=120)
        )
        if not data:
            raise MaxunError("Failed to create robot")
        return data

    async def update_robot(self, robot_id: str, updates: dict):
        data = await self._handle(
            self.client.put(f"/robots/{robot_id}", json=updates)
        )
        if not data:
            raise MaxunError(f"Failed to update robot {robot_id}")
        return data

    async def delete_robot(self, robot_id: str):
        await self._handle(self.client.delete(f"/robots/{robot_id}"))

    async def duplicate_robot(self, robot_id: str, target_url: str):
        return await self._handle(
            self.client.post(f"/robots/{robot_id}/duplicate", json={"targetUrl": target_url})
        )

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
        data = await self._handle(self.client.get(f"/robots/{robot_id}/runs"))
        return data or []

    async def get_run(self, robot_id: str, run_id: str):
        data = await self._handle(
            self.client.get(f"/robots/{robot_id}/runs/{run_id}")
        )
        if not data:
            raise MaxunError(f"Run {run_id} not found", 404)
        return data

    async def abort_run(self, robot_id: str, run_id: str):
        await self._handle(
            self.client.post(f"/robots/{robot_id}/runs/{run_id}/abort")
        )

    async def schedule_robot(self, robot_id: str, schedule: dict):
        data = await self._handle(
            self.client.put(f"/robots/{robot_id}", json={"schedule": schedule})
        )
        if not data:
            raise MaxunError(f"Failed to schedule robot {robot_id}")
        return data

    async def unschedule_robot(self, robot_id: str):
        data = await self._handle(
            self.client.put(f"/robots/{robot_id}", json={"schedule": None})
        )
        if not data:
            raise MaxunError(f"Failed to unschedule robot {robot_id}")
        return data

    async def add_webhook(self, robot_id: str, webhook: dict):
        robot = await self.get_robot(robot_id)
        webhooks = list(robot.get("webhooks") or [])

        now = datetime.now(timezone.utc).isoformat()
        new_webhook = {
            "id": f"webhook_{int(time.time() * 1000)}",
            "url": webhook["url"],
            "events": webhook.get("events") or ["run.completed", "run.failed"],
            "active": True,
            "createdAt": now,
            "updatedAt": now,
        }
        webhooks.append(new_webhook)

        data = await self._handle(
            self.client.put(f"/robots/{robot_id}", json={"webhooks": webhooks})
        )
        if not data:
            raise MaxunError(f"Failed to add webhook to robot {robot_id}")
        return data

    async def extract_with_llm(self, options: dict):
        return await self._handle(
            self.client.post("/extract/llm", json=options, timeout=300)
        )

    async def create_document_robot(
        self,
        file: Union[str, bytes],
        prompt: str,
        robot_name: Optional[str] = None,
        ollama_model: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> dict:
        """Create a document-extraction robot from a PDF file path or bytes."""
        if isinstance(file, str):
            file_name = file_name or os.path.basename(file)
            with open(file, 'rb') as f:
                file_bytes = f.read()
        else:
            file_bytes = file
            file_name = file_name or 'document.pdf'

        data = {'prompt': prompt}
        if robot_name:
            data['robotName'] = robot_name
        if ollama_model:
            data['ollamaModel'] = ollama_model

        response = await self.client.post(
            '/robots/document',
            files={'file': (file_name, file_bytes, 'application/pdf')},
            data=data,
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get('data') and not body.get('robot'):
            raise MaxunError('Failed to create document robot')
        return body

    async def create_crawl_robot(self, url: str, options: dict):
        return await self._handle(
            self.client.post("/crawl", json={"url": url, **options})
        )

    async def create_search_robot(self, options: dict):
        return await self._handle(
            self.client.post("/search", json=options)
        )