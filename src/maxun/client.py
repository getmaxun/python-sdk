"""Low-level HTTP client for the Maxun SDK API.

Most people should use :class:`maxun.Maxun` (or the ``Scrape``/``Crawl``/...
classes) instead of calling this directly. Every method here maps to exactly one
server endpoint, except the webhook helpers, which read the robot first.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import httpx

from ._utils import get_field, load_document, to_payload, warn
from .llm_options import build_llm_payload
from .types import (
    WEBHOOK_EVENTS,
    AuthenticationError,
    Config,
    ConflictError,
    ExecutionOptions,
    ListLimitUpdate,
    MaxunError,
    NotFoundError,
    RunFailedError,
    ScheduleConfig,
    ValidationError,
    WebhookConfig,
)

DOCUMENT_PARSE_FORMATS = ("markdown", "html", "links", "summary")

_LEGACY_EVENT_NAMES = {"run.completed": "run_completed", "run.failed": "run_failed"}


def _error_from_response(response: httpx.Response, path: str) -> MaxunError:
    try:
        payload = response.json()
    except Exception:
        payload = None

    message = None
    if isinstance(payload, dict):
        error, detail = payload.get("error"), payload.get("message")
        message = error or detail
        if error and detail and detail != error:
            message = f"{error}: {detail}"
        if isinstance(payload.get("details"), str):
            message = f"{message} ({payload['details']})" if message else payload["details"]
    if not message:
        message = (response.text or "").strip()[:500] or f"HTTP {response.status_code}"

    status = response.status_code
    if path.endswith("/execute") and status >= 500:
        cls = RunFailedError
    elif status in (401, 403):
        cls = AuthenticationError
    elif status == 404:
        cls = NotFoundError
    elif status == 409:
        cls = ConflictError
    elif status in (400, 422):
        cls = ValidationError
    else:
        cls = MaxunError
    return cls(message, status_code=status, details=payload)


def _schedule_payload(schedule: Union[ScheduleConfig, Dict[str, Any]]) -> Dict[str, Any]:
    payload = to_payload(schedule)
    for read_only in ("cronExpression", "lastRunAt", "nextRunAt"):
        payload.pop(read_only, None)
    if not payload.get("runEvery") or not payload.get("runEveryUnit"):
        raise ValueError("A schedule needs run_every and run_every_unit, e.g. run_every=6, run_every_unit='HOURS'.")
    payload["runEveryUnit"] = str(payload["runEveryUnit"]).upper()
    if payload.get("startFrom"):
        payload["startFrom"] = str(payload["startFrom"]).upper()
    payload.setdefault("timezone", "UTC")
    return payload


def _normalize_events(events: Optional[List[str]]) -> List[str]:
    if not events:
        return list(WEBHOOK_EVENTS)
    normalized = []
    for event in events:
        if event in _LEGACY_EVENT_NAMES:
            warn(
                f'Webhook event "{event}" is spelled "{_LEGACY_EVENT_NAMES[event]}" by the server; '
                "using that. Webhooks saved with the dotted name never fired."
            )
            event = _LEGACY_EVENT_NAMES[event]
        if event not in WEBHOOK_EVENTS:
            raise ValueError(f'Unknown webhook event "{event}". Use one of: {", ".join(WEBHOOK_EVENTS)}.')
        if event not in normalized:
            normalized.append(event)
    return normalized


def _webhook_entry(webhook: Union[str, WebhookConfig, Dict[str, Any]], existing: Optional[dict] = None) -> dict:
    if isinstance(webhook, str):
        webhook = {"url": webhook}
    url = get_field(webhook, "url")
    if not url:
        raise ValueError("A webhook needs a url.")
    if get_field(webhook, "headers"):
        warn("Maxun does not send custom webhook headers; the headers you passed are ignored.")

    now = datetime.now(timezone.utc).isoformat()
    entry = dict(existing or {})
    entry.update({
        "id": entry.get("id") or f"webhook_{uuid.uuid4().hex}",
        "url": url,
        "events": _normalize_events(get_field(webhook, "events")),
        "active": True,
        "createdAt": entry.get("createdAt") or now,
        "updatedAt": now,
    })
    for key, names in (
        ("retryAttempts", ("retry_attempts", "retryAttempts")),
        ("retryDelay", ("retry_delay", "retryDelay")),
        ("timeout", ("timeout",)),
    ):
        value = get_field(webhook, *names)
        if value is not None:
            entry[key] = value
    return entry


class Client:
    """Thin async wrapper over the Maxun SDK HTTP API.

    One ``Client`` owns one connection pool. Close it with ``await client.close()``
    or use ``async with``.
    """

    def __init__(self, config: Optional[Config] = None):
        config = config or Config()
        self.config = config
        self.api_key = config.api_key
        self.base_url = config.base_url

        headers = {"x-api-key": self.api_key}
        if config.team_id:
            headers["x-team-id"] = config.team_id

        # Content-Type is left to httpx so multipart uploads get the right header.
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=config.timeout)

    # ---------- lifecycle ----------

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ---------- plumbing ----------

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Send a request and return the parsed JSON body, raising MaxunError on failure."""
        path = path.lstrip("/")
        try:
            response = await self.client.request(method, path, **kwargs)
        except httpx.TimeoutException as e:
            raise MaxunError(f"Request to {path} timed out", details=str(e)) from e
        except httpx.RequestError as e:
            raise MaxunError(f"Could not reach Maxun at {self.base_url}: {e}", details=str(e)) from e

        if response.status_code >= 400:
            raise _error_from_response(response, path)
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as e:
            raise MaxunError(
                f"Maxun returned a non-JSON response for {path}. Is base_url ({self.base_url}) "
                "pointing at the SDK API (it should end in /api/sdk/)?",
                status_code=response.status_code,
                details=response.text[:500],
            ) from e

    async def _data(self, method: str, path: str, **kwargs: Any) -> Any:
        body = await self._request(method, path, **kwargs)
        return body.get("data") if isinstance(body, dict) else body

    async def _handle(self, request: Any) -> Any:
        """Kept for backwards compatibility; prefer ``_data``."""
        try:
            response = await request
        except httpx.RequestError as e:
            raise MaxunError("No response from server", details=str(e)) from e
        if response.status_code >= 400:
            raise _error_from_response(response, str(response.request.url.path))
        body = response.json()
        return body.get("data") if isinstance(body, dict) else body

    # ---------- account ----------

    async def get_status(self) -> dict:
        """Account info for this API key (email, plan, credits)."""
        return await self._request("GET", "status")

    # ---------- robots ----------

    async def get_robots(self) -> List[dict]:
        return await self._data("GET", "robots") or []

    async def get_robot(self, robot_id: str) -> dict:
        data = await self._data("GET", f"robots/{robot_id}")
        if not data:
            raise NotFoundError(f"Robot {robot_id} not found", 404)
        return data

    async def create_robot(self, workflow_file: dict) -> dict:
        meta = dict(workflow_file.get("meta") or {})
        monitor = meta.pop("monitor", None)
        robot_type = meta.pop("robotType", None) or meta.get("type")
        meta["type"] = robot_type
        if monitor is not None:
            meta["compareRuns"] = bool(monitor)
        payload = {**workflow_file, "meta": meta}
        data = await self._data("POST", "robots", json=payload, timeout=120)
        if not data:
            raise MaxunError("Failed to create robot")
        return data

    async def update_robot(self, robot_id: str, updates: dict) -> dict:
        payload = dict(updates)
        if payload.get("meta") is not None:
            meta = dict(payload["meta"])
            monitor = meta.pop("monitor", None)
            if monitor is not None:
                meta["compareRuns"] = bool(monitor)
            payload["meta"] = meta
        data = await self._data("PUT", f"robots/{robot_id}", json=payload)
        if not data:
            raise MaxunError(f"Failed to update robot {robot_id}")
        return data

    async def update_list_limits(self, robot_id: str, limits: List[ListLimitUpdate]) -> dict:
        """Update one or more list limits without resending the workflow."""
        return await self.update_robot(robot_id, {"limits": limits})

    async def delete_robot(self, robot_id: str) -> None:
        await self._request("DELETE", f"robots/{robot_id}")

    async def duplicate_robot(self, robot_id: str, target_url: str) -> dict:
        return await self._data("POST", f"robots/{robot_id}/duplicate", json={"targetUrl": target_url})

    # ---------- runs ----------

    async def execute_robot(
        self,
        robot_id: str,
        options: Optional[Union[ExecutionOptions, Dict[str, Any]]] = None,
    ) -> dict:
        """Run a robot and wait for it to finish. Returns the run result.

        Raises :class:`RunFailedError` if the run fails or is aborted.
        """
        options = options or {}
        if get_field(options, "params") is not None or get_field(options, "webhook") is not None:
            warn(
                "run(params=..., webhook=...) was never used by the server and is ignored. "
                "Use robot.add_webhook() to get notified about runs."
            )
        body: Dict[str, Any] = {}
        formats = get_field(options, "formats")
        if formats:
            body["formats"] = list(formats)
        prompt = get_field(options, "smart_queries", "smartQueries", "prompt_instructions", "promptInstructions")
        if prompt:
            body["promptInstructions"] = str(prompt).strip()

        timeout = get_field(options, "timeout")
        # Runs can legitimately take a long time (the server waits up to 3 hours),
        # so by default only the connection attempt is time-limited.
        request_timeout = (
            httpx.Timeout(float(timeout), connect=self.config.timeout)
            if timeout
            else httpx.Timeout(None, connect=self.config.timeout)
        )
        try:
            data = await self._data("POST", f"robots/{robot_id}/execute", json=body, timeout=request_timeout)
        except MaxunError as e:
            if timeout and "timed out" in e.message:
                raise MaxunError(
                    f"Run did not finish within {timeout}s. It may still be running on the server; "
                    "check robot.get_latest_run().",
                    details=e.details,
                ) from e
            raise
        if not data:
            raise MaxunError("Failed to execute robot")
        return data

    async def get_runs(self, robot_id: str) -> List[dict]:
        return await self._data("GET", f"robots/{robot_id}/runs") or []

    async def get_run(self, robot_id: str, run_id: str) -> dict:
        data = await self._data("GET", f"robots/{robot_id}/runs/{run_id}")
        if not data:
            raise NotFoundError(f"Run {run_id} not found", 404)
        return data

    async def get_run_diff(self, robot_id: str, run_id: str, format: Optional[str] = None) -> dict:
        """Return the monitoring diff between a run and the previous successful run."""
        data = await self._data(
            "GET",
            f"robots/{robot_id}/runs/{run_id}/diff",
            params={"format": format} if format else None,
        )
        if not data:
            raise NotFoundError(f"Monitoring diff for run {run_id} was not found", 404)
        return data

    async def abort_run(self, robot_id: str, run_id: str) -> None:
        await self._request("POST", f"robots/{robot_id}/runs/{run_id}/abort")

    # ---------- schedule ----------

    async def schedule_robot(self, robot_id: str, schedule: Union[ScheduleConfig, Dict[str, Any]]) -> dict:
        return await self.update_robot(robot_id, {"schedule": _schedule_payload(schedule)})

    async def unschedule_robot(self, robot_id: str) -> dict:
        return await self.update_robot(robot_id, {"schedule": None})

    # ---------- webhooks ----------

    async def add_webhook(self, robot_id: str, webhook: Union[str, WebhookConfig, Dict[str, Any]]) -> dict:
        """Add a webhook, or update the existing one with the same URL."""
        robot = await self.get_robot(robot_id)
        webhooks = list(robot.get("webhooks") or [])
        url = webhook if isinstance(webhook, str) else get_field(webhook, "url")
        existing_index = next((i for i, w in enumerate(webhooks) if w.get("url") == url), None)
        if existing_index is None:
            webhooks.append(_webhook_entry(webhook))
        else:
            webhooks[existing_index] = _webhook_entry(webhook, webhooks[existing_index])
        return await self.update_robot(robot_id, {"webhooks": webhooks})

    async def remove_webhook(self, robot_id: str, id_or_url: str) -> dict:
        robot = await self.get_robot(robot_id)
        webhooks = list(robot.get("webhooks") or [])
        remaining = [w for w in webhooks if id_or_url not in (w.get("id"), w.get("url"))]
        if len(remaining) == len(webhooks):
            raise NotFoundError(f"No webhook with id or url {id_or_url!r} on robot {robot_id}", 404)
        return await self.update_robot(robot_id, {"webhooks": remaining or None})

    # ---------- robot creation endpoints ----------

    async def extract_with_llm(self, options: dict) -> dict:
        payload = {k: v for k, v in dict(options).items() if v is not None}
        monitor = payload.pop("monitor", None)
        if monitor is not None:
            payload["compareRuns"] = bool(monitor)
        return await self._data("POST", "extract/llm", json=payload, timeout=300)

    async def create_crawl_robot(self, url: str, options: dict) -> dict:
        return await self._data("POST", "crawl", json={"url": url, **options}, timeout=120)

    async def create_search_robot(self, options: dict) -> dict:
        return await self._data("POST", "search", json=options, timeout=120)

    async def create_document_extract_robot(
        self,
        file: Union[str, bytes],
        prompt: str,
        robot_name: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> dict:
        """Create a document-extraction robot. Returns the raw response body
        (``{"data": robot, "extractionSchema": ...}``)."""
        if not prompt or not prompt.strip():
            raise ValueError("prompt is required")
        name, data, content_type = load_document(file, file_name)
        form = {"prompt": prompt.strip()}
        if robot_name:
            form["robotName"] = robot_name
        form.update(build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url))
        body = await self._request(
            "POST", "robots/document", files={"file": (name, data, content_type)}, data=form, timeout=300
        )
        if not body.get("data"):
            raise MaxunError("Failed to create document robot", details=body)
        return body

    async def create_document_parse_robot(
        self,
        file: Union[str, bytes],
        output_formats: Optional[List[str]] = None,
        robot_name: Optional[str] = None,
        file_name: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> dict:
        """Create a document-parse robot. ``output_formats`` defaults to all of
        markdown, html, links and summary. Returns the raw response body."""
        formats = list(output_formats or [])
        invalid = [f for f in formats if f not in DOCUMENT_PARSE_FORMATS]
        if invalid:
            raise ValueError(
                f"Invalid document formats: {', '.join(map(str, invalid))}. "
                f"Use any of: {', '.join(DOCUMENT_PARSE_FORMATS)}."
            )
        name, data, content_type = load_document(file, file_name)
        form: Dict[str, Any] = {}
        if robot_name:
            form["robotName"] = robot_name
        form.update(build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url))
        files: List[Any] = [("file", (name, data, content_type))]
        files.extend(("outputFormats[]", (None, fmt)) for fmt in formats)
        body = await self._request("POST", "robots/document-parse", files=files, data=form, timeout=300)
        if not body.get("data"):
            raise MaxunError("Failed to create document-parse robot", details=body)
        return body
