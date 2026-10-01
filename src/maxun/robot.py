from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ._monitoring import compare_crawl, crawl_diff, crawl_pages, previous_successful_run
from ._utils import warn
from .client import Client
from .types import Format, MaxunError, TimeUnit, WebhookEvent


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


def result_from_run(raw: dict, monitored: Optional[bool] = None) -> "RunResult":
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
    return RunResult(
        {
            "runId": raw.get("runId"),
            "status": raw.get("status"),
            "hasChanges": bool(raw.get("hasChanges")),
            "changedFormats": (output.get("_comparison") or {}).get("changedFormats") or [],
            "data": data,
            "screenshots": list((raw.get("binaryOutput") or {}).values()),
        },
        monitored=monitored,
    )


class Run(dict):
    """One run of a robot.

    It is a plain dict of the run's summary, so printing it or ``json.dumps``
    gives exactly::

        {"id": "...", "runId": "...", "robotId": "...", "name": "Example",
         "status": "success", "startedAt": "2026-10-01T00:46:25Z", "finishedAt": "2026-10-01T00:47:14Z"}

    Times are ISO 8601 in UTC. The run's output is in ``run.result`` (a
    :class:`RunResult`, like the one ``robot.run()`` returns) and the raw server
    record in ``run.get_data()``. Other raw fields, like
    ``run["serializableOutput"]``, can still be read.
    """

    def __init__(self, raw: Optional[dict] = None, monitored: Optional[bool] = None):
        raw = dict(raw or {})
        super().__init__({
            "id": raw.get("id"),
            "runId": raw.get("runId"),
            "robotId": raw.get("robotMetaId"),
            "name": raw.get("name"),
            "status": raw.get("status"),
            "startedAt": _to_iso(raw.get("startedAt")),
            "finishedAt": _to_iso(raw.get("finishedAt")),
        })
        self._raw = raw
        self._monitored = monitored

    # Older code read the raw record (run["serializableOutput"], run.get("hasChanges")).
    def __missing__(self, key: str) -> Any:
        raw = self.__dict__.get("_raw", {})
        if key in raw:
            return raw[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if dict.__contains__(self, key):
            return dict.__getitem__(self, key)
        return self.__dict__.get("_raw", {}).get(key, default)

    @property
    def id(self) -> Optional[str]:
        return self["id"]

    @property
    def run_id(self) -> Optional[str]:
        return self["runId"]

    @property
    def robot_id(self) -> Optional[str]:
        return self["robotId"]

    @property
    def name(self) -> Optional[str]:
        return self["name"]

    @property
    def status(self) -> Optional[str]:
        """``queued``, ``running``, ``success``, ``failed``, ``aborting`` or ``aborted``."""
        return self["status"]

    @property
    def started_at(self) -> Optional[str]:
        return self["startedAt"]

    @property
    def finished_at(self) -> Optional[str]:
        return self["finishedAt"]

    @property
    def has_changes(self) -> bool:
        return bool(self._raw.get("hasChanges"))

    @property
    def result(self) -> "RunResult":
        """The run's output, in the same shape ``robot.run()`` returns."""
        return result_from_run(self._raw, self._monitored)

    def to_dict(self) -> Dict[str, Any]:
        """The summary fields, as a plain dict."""
        return dict(self)

    def get_data(self) -> dict:
        """The raw run record returned by the server."""
        return self._raw


MONITORABLE_TYPES = ("scrape", "crawl", "extract")


# (key in the result, key in the server's run data)
_RESULT_FIELDS = (
    ("text", "text"),
    ("markdown", "markdown"),
    ("html", "html"),
    ("summary", "summary"),
    ("links", "links"),
    ("textData", "textData"),
    ("listData", "listData"),
    ("crawlData", "crawlData"),
    ("searchData", "searchData"),
    ("smartQueryResult", "promptResult"),
    ("documentData", "documentData"),
)


def _has_value(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _result_fields(raw: dict, monitored: Optional[bool]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"runId": raw.get("runId"), "status": raw.get("status")}
    data = raw.get("data") or {}
    for key, source in _RESULT_FIELDS:
        if _has_value(data.get(source)):
            out[key] = data[source]
    if raw.get("screenshots"):
        out["screenshots"] = raw["screenshots"]
    if monitored is None:
        monitored = bool(raw.get("hasChanges") or raw.get("changedFormats") or raw.get("changedPages"))
    if monitored:
        out["hasChanges"] = bool(raw.get("hasChanges"))
        out["changedFormats"] = list(raw.get("changedFormats") or [])
        if raw.get("changedPages") is not None:
            out["changedPages"] = raw["changedPages"]
    return out


class RunResult(dict):
    """The result of ``robot.run()``.

    It holds the run id, the status and only the outputs the run produced,
    e.g. ``{"runId": ..., "status": "success", "markdown": "...", "screenshots": [...]}``.
    ``hasChanges`` and ``changedFormats`` are included when the robot has
    change monitoring on.

    Attributes read the same values, and are always safe to use (an output the
    run didn't produce is ``None`` or empty):

    - ``run_id``, ``status``
    - ``markdown``, ``html``, ``text``, ``summary``, ``links`` - page content
    - ``text_data`` - fields captured with ``capture_text`` (dict)
    - ``list_data`` - items captured with ``capture_list`` or prompt extraction (list)
    - ``crawl_data`` - one entry per crawled page (list)
    - ``search_data`` - search results (dict)
    - ``smart_query_result`` - the LLM's answer to a Smart Query
    - ``document_data`` - data pulled from a file by a document-extract robot
    - ``screenshots`` - screenshots taken during the run
    - ``has_changes``, ``changed_formats``, ``changed_pages`` - monitoring results

    Code written for 0.0.x, like ``result["data"]["listData"]``, still works.
    """

    def __init__(self, raw: Optional[dict] = None, monitored: Optional[bool] = None):
        raw = dict(raw or {})
        super().__init__(_result_fields(raw, monitored))
        self._raw = raw

    # Older code read the server's shape (result["data"], result.get("screenshots")).
    def __missing__(self, key: str) -> Any:
        raw = self.__dict__.get("_raw", {})
        if key in raw:
            return raw[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if dict.__contains__(self, key):
            return dict.__getitem__(self, key)
        return self.__dict__.get("_raw", {}).get(key, default)

    @property
    def run_id(self) -> Optional[str]:
        return self._raw.get("runId")

    @property
    def status(self) -> Optional[str]:
        return self._raw.get("status")

    @property
    def data(self) -> Dict[str, Any]:
        """The server's raw output, as 0.0.x returned it."""
        return self._raw.get("data") or {}

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
        return self._raw.get("screenshots") or []

    @property
    def has_changes(self) -> bool:
        return bool(self._raw.get("hasChanges"))

    @property
    def changed_formats(self) -> List[str]:
        return self._raw.get("changedFormats") or []

    @property
    def changed_pages(self) -> Dict[str, List[str]]:
        return self._raw.get("changedPages") or {"added": [], "removed": [], "changed": []}


class Robot(dict):
    """A robot saved on your Maxun account. Every create/get method returns one.

    It is a plain dict of the robot's id, name and type, so printing it or
    ``json.dumps`` gives exactly ``{"id": "...", "name": "...", "type": "extract"}``.
    Everything else is available as attributes and methods (``robot.url``,
    ``robot.run()``, ``robot.get_data()`` for the raw record, ...).
    """

    def __init__(self, client: Client, robot_data: dict):
        super().__init__()
        self._client = client
        self.robot_data = robot_data

    @property
    def client(self) -> Client:
        return self._client

    @property
    def robot_data(self) -> dict:
        return self._data

    @robot_data.setter
    def robot_data(self, value: dict) -> None:
        self._data = value or {}
        meta = self._data.get("recording_meta") or {}
        dict.clear(self)
        dict.update(self, {
            "id": meta.get("id"),
            "name": meta.get("name", ""),
            "type": meta.get("type") or meta.get("robotType"),
        })

    def to_dict(self) -> Dict[str, Any]:
        """The robot's id, name and type, as a plain dict."""
        return dict(self)

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(("Robot", self.id))

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
        options: Optional[Dict[str, Any]] = None,
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
        raw = dict(await self.client.execute_robot(self.id, merged))
        await self._add_missing_outputs(raw, merged.get("formats") or self.formats)
        if self.type == "crawl" and self.is_monitoring:
            await self._compare_crawl_run(raw)
        return RunResult(raw, monitored=self.is_monitoring)

    async def _compare_crawl_run(self, result: dict) -> None:
        """The server does not compare crawl runs, so the SDK does it."""
        run_id = result.get("runId")
        if not run_id:
            return
        try:
            runs = await self._raw_runs()
        except MaxunError as e:
            warn(f"The run succeeded but could not be compared with the previous run: {e}")
            return
        current = next((r for r in runs if r.get("runId") == run_id), None)
        output = (current or {}).get("serializableOutput") or {}
        if "_comparison" in output:
            return  # the server compared it
        previous = previous_successful_run(runs, run_id)
        if previous is None:
            result["changedPages"] = {"added": [], "removed": [], "changed": []}
            return
        changed_formats, pages = compare_crawl(
            crawl_pages((previous.get("serializableOutput") or {}).get("crawl")),
            crawl_pages(output.get("crawl")) or (result.get("data") or {}).get("crawlData") or [],
        )
        result["hasChanges"] = bool(changed_formats)
        result["changedFormats"] = changed_formats
        result["changedPages"] = pages

    async def _add_missing_outputs(self, result: dict, formats: List[str]) -> None:
        """The run endpoint leaves out links and document-extract data, so read
        them from the stored run."""
        wants_links = "links" in (formats or [])
        is_document = self.type == "doc-extract"
        if not (wants_links or is_document) or not result.get("runId"):
            return
        try:
            run = await self.client.get_run(self.id, result["runId"])
        except MaxunError as e:
            warn(f"The run succeeded but its links/document data could not be loaded: {e}")
            return
        output = run.get("serializableOutput") or {}
        data = dict(result.get("data") or {})
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
        return [Run(raw, self.is_monitoring) for raw in await self._raw_runs()]

    async def get_run(self, run_id: str) -> Run:
        return Run(await self.client.get_run(self.id, run_id), self.is_monitoring)

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
        _legacy: Optional[Dict[str, Any]] = None,
        /,
        *,
        run_every: Optional[int] = None,
        run_every_unit: Optional[TimeUnit] = None,
        timezone: Optional[str] = None,
        start_from: Optional[str] = None,
        day_of_month: Optional[int] = None,
        at_time_start: Optional[str] = None,
        at_time_end: Optional[str] = None,
    ) -> dict:
        """Run the robot on a schedule. Returns the saved schedule::

            await robot.schedule(run_every=6, run_every_unit="HOURS", timezone="Asia/Kolkata")

        ``run_every_unit``: MINUTES, HOURS, DAYS, WEEKS or MONTHS. ``timezone``
        defaults to UTC. ``start_from`` is the weekday for weekly schedules,
        ``day_of_month`` the day for monthly ones; ``at_time_start`` /
        ``at_time_end`` ("HH:MM") limit the hours it runs in.
        """
        options = {
            key: value
            for key, value in (
                ("run_every", run_every),
                ("run_every_unit", run_every_unit),
                ("timezone", timezone),
                ("start_from", start_from),
                ("day_of_month", day_of_month),
                ("at_time_start", at_time_start),
                ("at_time_end", at_time_end),
            )
            if value is not None
        }
        if _legacy is not None:
            if options:
                raise TypeError("Pass the schedule as keyword arguments only, e.g. robot.schedule(run_every=6, run_every_unit='HOURS').")
            options = _legacy
        self.robot_data = await self.client.schedule_robot(self.id, options)
        return self._saved_schedule() or {}

    async def unschedule(self) -> None:
        """Stop running the robot on a schedule."""
        self.robot_data = await self.client.unschedule_robot(self.id)

    async def get_schedule(self) -> Optional[dict]:
        """The robot's schedule (with ``nextRunAt`` and ``cronExpression``), or
        ``None`` if it has none."""
        await self.refresh()
        return self._saved_schedule()

    def _saved_schedule(self) -> Optional[dict]:
        return self.robot_data.get("schedule") or None

    # ---------- webhooks ----------

    async def add_webhook(
        self,
        url: Optional[str] = None,
        *,
        events: Optional[List[WebhookEvent]] = None,
        retry_attempts: Optional[int] = None,
        retry_delay: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """Get a POST to ``url`` when a run completes or fails. Returns the saved webhook::

            await robot.add_webhook("https://example.com/hook", events=["run_failed"], retry_attempts=5)

        ``events`` defaults to both ``run_completed`` and ``run_failed``.
        Adding a URL that is already registered updates it instead of duplicating it.
        """
        if url is None:
            raise TypeError("add_webhook() needs a URL, e.g. robot.add_webhook('https://example.com/hook')")
        if isinstance(url, str):
            webhook: Any = {
                "url": url,
                "events": events,
                "retry_attempts": retry_attempts,
                "retry_delay": retry_delay,
                "timeout": timeout,
            }
        else:  # a dict or a WebhookConfig from older code
            webhook = url
            url = webhook.get("url") if isinstance(webhook, dict) else webhook.url
        self.robot_data = await self.client.add_webhook(self.id, webhook)
        return next(w for w in self._saved_webhooks() if w.get("url") == url)

    async def get_webhooks(self) -> List[dict]:
        """The robot's webhooks (``[]`` if none)."""
        await self.refresh()
        return self._saved_webhooks()

    def _saved_webhooks(self) -> List[dict]:
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
