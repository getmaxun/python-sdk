from typing import Any, Dict, List, Optional, Union

from .client import Client
from .types import ExecutionOptions, Format, MaxunError, ScheduleConfig, WebhookConfig


class RunResult(dict):
    """The result of ``robot.run()``.

    It is a plain dict (so ``result["data"]["listData"]`` keeps working) with
    attributes for the common fields:

    - ``run_id``, ``status``
    - ``markdown``, ``html``, ``text``, ``summary`` - scrape/crawl page content
    - ``text_data`` - fields captured with ``capture_text`` (dict)
    - ``list_data`` - items captured with ``capture_list`` or LLM extraction (list)
    - ``crawl_data`` - one entry per crawled page (list)
    - ``search_data`` - search results (dict)
    - ``smart_query_result`` - the LLM's answer to a Smart Query
    - ``links`` - URLs found on the page (when the ``links`` format is on)
    - ``document_data`` - data pulled from a file by a document-extract robot
    - ``screenshots`` - screenshots taken during the run
    - ``has_changes``, ``changed_formats`` - monitoring results
    """

    @property
    def run_id(self) -> Optional[str]:
        return self.get("runId")

    @property
    def status(self) -> Optional[str]:
        return self.get("status")

    @property
    def data(self) -> Dict[str, Any]:
        return self.get("data") or {}

    @property
    def markdown(self) -> Optional[str]:
        return self.data.get("markdown")

    @property
    def html(self) -> Optional[str]:
        return self.data.get("html")

    @property
    def text(self) -> Optional[str]:
        return self.data.get("text")

    @property
    def summary(self) -> Optional[str]:
        return self.data.get("summary")

    @property
    def text_data(self) -> Dict[str, Any]:
        return self.data.get("textData") or {}

    @property
    def list_data(self) -> List[Any]:
        return self.data.get("listData") or []

    @property
    def crawl_data(self) -> List[Any]:
        return self.data.get("crawlData") or []

    @property
    def search_data(self) -> Dict[str, Any]:
        return self.data.get("searchData") or {}

    @property
    def smart_query_result(self) -> Optional[str]:
        return self.data.get("promptResult")

    @property
    def links(self) -> List[Any]:
        return self.data.get("links") or []

    @property
    def document_data(self) -> Any:
        return self.data.get("documentData")

    @property
    def screenshots(self) -> List[Any]:
        return self.get("screenshots") or []

    @property
    def has_changes(self) -> bool:
        return bool(self.get("hasChanges"))

    @property
    def changed_formats(self) -> List[str]:
        return self.get("changedFormats") or []


class Robot:
    """A robot saved on your Maxun account. Every create/get method returns one."""

    def __init__(self, client: Client, robot_data: dict):
        self.client = client
        self.robot_data = robot_data

    def __repr__(self) -> str:
        return f"<Robot id={self.id!r} name={self.name!r} type={self.type!r}>"

    # ---------- properties ----------

    @property
    def meta(self) -> dict:
        return self.robot_data.get("recording_meta") or {}

    @property
    def id(self) -> str:
        return self.meta["id"]

    @property
    def name(self) -> str:
        return self.meta.get("name", "")

    @property
    def type(self) -> Optional[str]:
        """``extract``, ``scrape``, ``crawl``, ``search``, ``doc-extract`` or ``doc-parse``."""
        return self.meta.get("type") or self.meta.get("robotType")

    @property
    def url(self) -> Optional[str]:
        return self.meta.get("url")

    @property
    def formats(self) -> List[str]:
        return list(self.meta.get("formats") or [])

    @property
    def is_monitoring(self) -> bool:
        """True if each run is compared with the previous successful run."""
        return bool(self.meta.get("compareRuns"))

    def get_data(self) -> dict:
        """The raw robot record returned by the server."""
        return self.robot_data

    # ---------- running ----------

    async def run(
        self,
        options: Optional[Union[ExecutionOptions, Dict[str, Any]]] = None,
        *,
        formats: Optional[List[Format]] = None,
        smart_queries: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> RunResult:
        """Run the robot and wait for it to finish.

        :param formats: Output formats for this run only (defaults to the robot's).
        :param smart_queries: A question for the LLM about the page, this run only.
        :param timeout: Seconds to wait. By default waits until the run finishes.
        :raises RunFailedError: if the run fails or is aborted.
        """
        merged: Dict[str, Any] = {}
        if options is not None:
            if isinstance(options, dict):
                merged.update(options)
            else:
                merged.update({k: getattr(options, k) for k in vars(options)})
        for key, value in (("formats", formats), ("smart_queries", smart_queries), ("timeout", timeout)):
            if value is not None:
                merged[key] = value
        result = RunResult(await self.client.execute_robot(self.id, merged))
        await self._add_missing_outputs(result, merged.get("formats") or self.formats)
        return result

    async def _add_missing_outputs(self, result: RunResult, formats: List[str]) -> None:
        """The run endpoint leaves out links and document-extract data, so read
        them from the stored run."""
        wants_links = "links" in (formats or [])
        is_document = self.type == "doc-extract"
        if not (wants_links or is_document) or not result.run_id:
            return
        run = await self.client.get_run(self.id, result.run_id)
        output = run.get("serializableOutput") or {}
        data = dict(result.data)
        if wants_links:
            links = output.get("links") or (output.get("scrape") or {}).get("links") or []
            data["links"] = [
                link["url"] if isinstance(link, dict) and "url" in link else link for link in links
            ]
        if is_document:
            data["documentData"] = (output.get("scrapeDoc") or {}).get("data")
        result["data"] = data

    async def get_runs(self) -> List[dict]:
        """All runs of this robot, newest first."""
        runs = await self.client.get_runs(self.id)
        return sorted(runs, key=lambda r: r.get("startedAt") or "", reverse=True)

    async def get_run(self, run_id: str) -> dict:
        return await self.client.get_run(self.id, run_id)

    async def get_latest_run(self) -> Optional[dict]:
        runs = await self.get_runs()
        return runs[0] if runs else None

    async def abort(self, run_id: str) -> None:
        """Abort a queued or running run."""
        await self.client.abort_run(self.id, run_id)

    # ---------- monitoring ----------

    async def set_monitoring(self, enabled: bool = True) -> None:
        """Turn change monitoring on or off. When on, every run is compared with
        the previous successful run; see ``result.has_changes`` and ``get_run_diff``."""
        await self.update({"meta": {"compareRuns": bool(enabled)}})

    async def get_run_diff(self, run_id: str, format: Optional[str] = None) -> dict:
        """What changed between a run and the previous successful run.

        ``format`` limits the diff to one output (e.g. ``"markdown"``,
        ``"captured-text"``, ``"captured-list"``).
        """
        return await self.client.get_run_diff(self.id, run_id, format)

    # ---------- schedule ----------

    async def schedule(
        self,
        config: Optional[Union[ScheduleConfig, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> dict:
        """Run the robot on a schedule. Returns the saved schedule.

        Either pass a :class:`ScheduleConfig` / dict, or keyword arguments::

            await robot.schedule(run_every=6, run_every_unit="HOURS", timezone="Asia/Kolkata")
        """
        if config is None:
            config = kwargs
        elif kwargs:
            raise TypeError("Pass either a schedule config or keyword arguments, not both.")
        self.robot_data = await self.client.schedule_robot(self.id, config)
        return self.get_schedule() or {}

    async def unschedule(self) -> None:
        self.robot_data = await self.client.unschedule_robot(self.id)

    def get_schedule(self) -> Optional[dict]:
        return self.robot_data.get("schedule") or None

    # ---------- webhooks ----------

    async def add_webhook(
        self,
        webhook: Optional[Union[str, WebhookConfig, Dict[str, Any]]] = None,
        *,
        events: Optional[List[str]] = None,
        retry_attempts: Optional[int] = None,
        retry_delay: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """Get a POST to ``url`` when a run completes or fails. Returns the saved webhook.

        ``webhook`` can be a URL string, a :class:`WebhookConfig` or a dict.
        Adding a URL that is already registered updates it instead of duplicating it.
        """
        if webhook is None:
            raise TypeError("add_webhook() needs a URL or a WebhookConfig")
        if isinstance(webhook, str):
            webhook = {
                "url": webhook,
                "events": events,
                "retry_attempts": retry_attempts,
                "retry_delay": retry_delay,
                "timeout": timeout,
            }
        url = webhook.get("url") if isinstance(webhook, dict) else webhook.url
        self.robot_data = await self.client.add_webhook(self.id, webhook)
        return next(w for w in self.get_webhooks() if w.get("url") == url)

    def get_webhooks(self) -> List[dict]:
        return list(self.robot_data.get("webhooks") or [])

    async def remove_webhook(self, id_or_url: str) -> None:
        """Remove one webhook by its id or URL."""
        self.robot_data = await self.client.remove_webhook(self.id, id_or_url)

    async def remove_webhooks(self) -> None:
        """Remove all webhooks."""
        self.robot_data = await self.client.update_robot(self.id, {"webhooks": None})

    # ---------- editing ----------

    async def update(self, updates: dict) -> None:
        """Send a raw update (``{"meta": {...}}``, ``{"workflow": [...]}``...)."""
        self.robot_data = await self.client.update_robot(self.id, updates)

    async def rename(self, name: str) -> None:
        await self.update({"meta": {"name": name}})

    async def set_list_limit(self, limit: int) -> None:
        """Set the item limit of this robot's list, crawl or search step
        (the first one, if there are several)."""
        supported_actions = {"scrapeList", "crawl", "search"}
        workflow = (self.robot_data.get("recording") or {}).get("workflow") or []

        for pair_index, pair in enumerate(workflow):
            for action_index, action in enumerate(pair.get("what") or []):
                if action.get("action") not in supported_actions:
                    continue
                for arg_index, arg in enumerate(action.get("args") or []):
                    if isinstance(arg, dict) and "limit" in arg:
                        self.robot_data = await self.client.update_list_limits(
                            self.id,
                            [{
                                "pairIndex": pair_index,
                                "actionIndex": action_index,
                                "argIndex": arg_index,
                                "limit": limit,
                            }],
                        )
                        return

        raise MaxunError("This robot has no list, crawl, or search step with a limit to update.")

    async def duplicate(self, target_url: str) -> "Robot":
        """Copy this robot to run against another URL. Returns the new robot."""
        new_robot_data = await self.client.duplicate_robot(self.id, target_url)
        return Robot(self.client, new_robot_data)

    async def delete(self) -> None:
        await self.client.delete_robot(self.id)

    async def refresh(self) -> None:
        """Reload this robot from the server."""
        self.robot_data = await self.client.get_robot(self.id)
