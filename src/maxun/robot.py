from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ._monitoring import compare_crawl, crawl_diff, crawl_pages, previous_successful_run
from ._utils import warn
from .client import Client
from .types import ExecutionOptions, Format, MaxunError, ScheduleConfig, WebhookConfig


def _clean_time(value: str) -> str:
    # Newer Node versions put a narrow no-break space before AM/PM.
    return value.replace("\u202f", " ").replace("\u00a0", " ").strip()


def _parse_time(value: Any) -> Optional[datetime]:
    """Run times come back as ISO strings or as "9/30/2026, 10:00:00 AM"."""
    if not isinstance(value, str):
        return None
    value = _clean_time(value)
    for parse in (
        lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None),
        lambda v: datetime.strptime(v, "%m/%d/%Y, %I:%M:%S %p"),
    ):
        try:
            return parse(value)
        except ValueError:
            continue
    return None


def _to_iso(value: Any) -> Optional[str]:
    """Normalise a run timestamp to ISO 8601 UTC ("2026-10-01T00:46:25Z").

    The server writes ``new Date().toLocaleString()`` ("9/30/2026, 10:00:00 AM"),
    which has no timezone; it is read as UTC, the default for Maxun deployments.
    Anything unrecognised is returned unchanged.
    """
    if not value or not isinstance(value, str):
        return None
    original, value = value, _clean_time(value)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%m/%d/%Y, %I:%M:%S %p")
        except ValueError:
            return original
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _first_content(value: Any) -> Optional[str]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0].get("content") or None
    return None


def result_from_run(raw: dict) -> "RunResult":
    """Build a RunResult from a stored run, the same way the server builds the
    result of ``robot.run()``."""
    output = raw.get("serializableOutput") or {}
    scrape = output.get("scrape") or {}

    list_data: List[Any] = []
    scrape_list = output.get("scrapeList")
    if isinstance(scrape_list, dict) and isinstance(scrape_list.get("scrapeList"), list):
        list_data = scrape_list["scrapeList"]
    elif isinstance(scrape_list, list):
        list_data = scrape_list
    elif isinstance(scrape_list, dict):
        first = next(iter(scrape_list.values()), None)
        list_data = first if isinstance(first, list) else []

    crawl = output.get("crawl")
    if isinstance(crawl, list):
        crawl_data = crawl
    elif isinstance(crawl, dict):
        first = next(iter(crawl.values()), None)
        crawl_data = first if isinstance(first, list) else []
    else:
        crawl_data = []

    def content(fmt: str) -> Optional[str]:
        return _first_content(output.get(fmt)) or _first_content(scrape.get(fmt))

    links = output.get("links") or scrape.get("links") or []
    data = {
        "textData": output.get("scrapeSchema") or {},
        "listData": list_data,
        "crawlData": crawl_data,
        "searchData": output.get("search") or {},
        "text": content("text"),
        "markdown": content("markdown"),
        "html": content("html"),
        "summary": content("summary"),
        "promptResult": _first_content(output.get("promptResult")),
        "links": [link["url"] if isinstance(link, dict) and "url" in link else link for link in links],
        "documentData": (output.get("scrapeDoc") or {}).get("data"),
    }
    return RunResult({
        "runId": raw.get("runId"),
        "status": raw.get("status"),
        "hasChanges": bool(raw.get("hasChanges")),
        "changedFormats": (output.get("_comparison") or {}).get("changedFormats") or [],
        "data": data,
        "screenshots": list((raw.get("binaryOutput") or {}).values()),
    })


class Run:
    """One run of a robot.

    Printing it shows only the summary fields; the run's output is in
    ``run.result`` (a :class:`RunResult`, like the one ``robot.run()`` returns)
    and the raw server record in ``run.get_data()``. ``run["runId"]``-style
    access to the raw record still works.
    """

    _SUMMARY = ("id", "run_id", "robot_id", "name", "status", "started_at", "finished_at")

    def __init__(self, raw: dict):
        self._raw = raw or {}

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def run_id(self) -> Optional[str]:
        return self._raw.get("runId")

    @property
    def robot_id(self) -> Optional[str]:
        return self._raw.get("robotMetaId")

    @property
    def name(self) -> Optional[str]:
        return self._raw.get("name")

    @property
    def status(self) -> Optional[str]:
        """``queued``, ``running``, ``success``, ``failed``, ``aborting`` or ``aborted``."""
        return self._raw.get("status")

    @property
    def started_at(self) -> Optional[str]:
        return _to_iso(self._raw.get("startedAt"))

    @property
    def finished_at(self) -> Optional[str]:
        return _to_iso(self._raw.get("finishedAt"))

    @property
    def has_changes(self) -> bool:
        return bool(self._raw.get("hasChanges"))

    @property
    def result(self) -> "RunResult":
        """The run's output, in the same shape ``robot.run()`` returns."""
        return result_from_run(self._raw)

    def to_dict(self) -> Dict[str, Any]:
        return {key: getattr(self, key) for key in self._SUMMARY}

    def get_data(self) -> dict:
        """The raw run record returned by the server."""
        return self._raw

    # Older code treated runs as dicts.
    def __getitem__(self, key: str) -> Any:
        return self._raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Run) and other._raw == self._raw

    def __repr__(self) -> str:
        fields = ", ".join(f"{key}={value!r}" for key, value in self.to_dict().items())
        return f"Run({fields})"


MONITORABLE_TYPES = ("scrape", "crawl", "extract")


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
    - ``changed_pages`` - crawl robots: ``{"added", "removed", "changed"}`` page URLs
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

    @property
    def changed_pages(self) -> Dict[str, List[str]]:
        return self.get("changedPages") or {"added": [], "removed": [], "changed": []}


class Robot:
    """A robot saved on your Maxun account. Every create/get method returns one."""

    def __init__(self, client: Client, robot_data: dict):
        self._client = client
        self._data = robot_data

    @property
    def client(self) -> Client:
        return self._client

    @property
    def robot_data(self) -> dict:
        return self._data

    @robot_data.setter
    def robot_data(self, value: dict) -> None:
        self._data = value

    def to_dict(self) -> Dict[str, Any]:
        """The robot's id, name and type."""
        return {"id": self.id, "name": self.name, "type": self.type}

    def __repr__(self) -> str:
        return f"Robot(id={self.id!r}, name={self.name!r}, type={self.type!r})"

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
        recording = self.robot_data.get("recording") or {}
        return list(self.meta.get("formats") or recording.get("outputFormats") or [])

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
        if self.type == "crawl" and self.is_monitoring:
            await self._compare_crawl_run(result)
        return result

    async def _compare_crawl_run(self, result: RunResult) -> None:
        """The server does not compare crawl runs, so the SDK does it."""
        if not result.run_id:
            return
        try:
            runs = await self._raw_runs()
        except MaxunError as e:
            warn(f"The run succeeded but could not be compared with the previous run: {e}")
            return
        current = next((r for r in runs if r.get("runId") == result.run_id), None)
        output = (current or {}).get("serializableOutput") or {}
        if "_comparison" in output:
            return  # the server compared it
        previous = previous_successful_run(runs, result.run_id)
        if previous is None:
            result["changedPages"] = {"added": [], "removed": [], "changed": []}
            return
        changed_formats, pages = compare_crawl(
            crawl_pages((previous.get("serializableOutput") or {}).get("crawl")),
            crawl_pages(output.get("crawl")) or result.crawl_data,
        )
        result["hasChanges"] = bool(changed_formats)
        result["changedFormats"] = changed_formats
        result["changedPages"] = pages

    async def _add_missing_outputs(self, result: RunResult, formats: List[str]) -> None:
        """The run endpoint leaves out links and document-extract data, so read
        them from the stored run."""
        wants_links = "links" in (formats or [])
        is_document = self.type == "doc-extract"
        if not (wants_links or is_document) or not result.run_id:
            return
        try:
            run = await self.client.get_run(self.id, result.run_id)
        except MaxunError as e:
            warn(f"The run succeeded but its links/document data could not be loaded: {e}")
            return
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

    async def _raw_runs(self) -> List[dict]:
        runs = await self.client.get_runs(self.id)
        keys = [_parse_time(r.get("startedAt")) for r in runs]
        if runs and all(k is not None for k in keys):
            return [r for _, r in sorted(zip(keys, runs), key=lambda pair: pair[0], reverse=True)]
        return runs  # the server already returns newest first

    async def get_runs(self) -> List[Run]:
        """All runs of this robot, newest first. Each run's output is in ``run.result``."""
        return [Run(raw) for raw in await self._raw_runs()]

    async def get_run(self, run_id: str) -> Run:
        return Run(await self.client.get_run(self.id, run_id))

    async def get_latest_run(self) -> Optional[Run]:
        runs = await self.get_runs()
        return runs[0] if runs else None

    async def abort(self, run_id: str) -> None:
        """Abort a queued or running run."""
        await self.client.abort_run(self.id, run_id)

    # ---------- monitoring ----------

    async def set_monitoring(self, enabled: bool = True) -> None:
        """Turn change monitoring on or off (scrape, crawl and extract robots).
        When on, every run is compared with the previous successful run; see
        ``result.has_changes`` and ``get_run_diff``."""
        if enabled and self.type not in MONITORABLE_TYPES:
            raise ValueError(
                f"Change monitoring works for scrape, crawl and extract robots, not {self.type} robots."
            )
        await self.update({"meta": {"compareRuns": bool(enabled)}})

    async def get_run_diff(self, run_id: str, format: Optional[str] = None) -> dict:
        """What changed between a run and the previous successful run.

        ``format`` limits the diff to one output: ``"markdown"``, ``"text"`` or
        ``"html"`` for scrape and crawl robots, ``"captured-text"`` or
        ``"captured-list"`` for extract robots. Crawl diffs also list the
        ``pages`` that were added, removed or changed.
        """
        if self.type == "crawl":
            runs = await self._raw_runs()
            current = next((r for r in runs if r.get("runId") == run_id), None)
            if current is None:
                current = await self.client.get_run(self.id, run_id)
            output = current.get("serializableOutput") or {}
            if "_comparison" not in output:
                return crawl_diff(run_id, previous_successful_run(runs, run_id), output.get("crawl"), format)
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
