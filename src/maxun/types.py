"""Public configuration types, literals and errors for the Maxun SDK.

Every config dataclass here can also be passed as a plain dict. Dict keys may be
snake_case (``run_every``) or camelCase (``runEvery``); both are accepted.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict

__all__ = [
    "RobotType", "RobotMode", "Format", "DocumentFormat", "RunStatus", "TimeUnit",
    "Weekday", "CrawlMode", "LLMProvider", "SearchMode", "SearchProvider",
    "SearchTimeRange", "PaginationType", "WebhookEvent",
    "Config", "ExtractFields",
    "Workflow", "WorkflowFile", "RobotData", "Run", "ApiResponse",
    "ListLimitUpdate",
    "MaxunError", "AuthenticationError", "NotFoundError", "ConflictError",
    "ValidationError", "RunFailedError",
    "DEFAULT_BASE_URL", "WEBHOOK_EVENTS",
]

# Older option classes. Every method now takes plain keyword arguments; these
# still import from ``maxun`` (with a DeprecationWarning) so old code runs.
DEPRECATED_CLASSES = (
    "ScheduleConfig", "WebhookConfig", "ExecutionOptions", "PaginationConfig",
    "ExtractListConfig", "CrawlConfig", "CrawlOptions", "SearchConfig", "SearchOptions",
)

# ======================
# Literals
# ======================

RobotType = Literal["extract", "scrape", "crawl", "search", "doc-extract", "doc-parse"]
RobotMode = Literal["normal", "bulk"]
Format = Literal["markdown", "html", "text", "links", "summary", "screenshot-visible", "screenshot-fullpage"]
DocumentFormat = Literal["markdown", "html", "links", "summary"]
RunStatus = Literal["running", "queued", "success", "failed", "aborting", "aborted"]
TimeUnit = Literal["MINUTES", "HOURS", "DAYS", "WEEKS", "MONTHS"]
Weekday = Literal["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
CrawlMode = Literal["domain", "subdomain", "path"]
LLMProvider = Literal["anthropic", "openai", "ollama"]
SearchMode = Literal["discover", "scrape"]
SearchProvider = Literal["duckduckgo"]
SearchTimeRange = Literal["day", "week", "month", "year"]
PaginationType = Literal["scrollDown", "scrollUp", "clickNext", "clickLoadMore", "none"]
WebhookEvent = Literal["run_completed", "run_failed"]

DEFAULT_BASE_URL = "https://app.maxun.dev/api/sdk/"
WEBHOOK_EVENTS = ("run_completed", "run_failed")


# ======================
# Client configuration
# ======================

@dataclass
class Config:
    """Connection settings.

    Anything left out is read from the environment: ``MAXUN_API_KEY``,
    ``MAXUN_BASE_URL`` and ``MAXUN_TEAM_ID``. ``base_url`` falls back to Maxun
    Cloud; for self-hosted Maxun use ``http://localhost:8080/api/sdk/`` (or
    wherever your backend runs).

    ``timeout`` (seconds) applies to ordinary API calls. Running a robot waits
    for the run to finish and has no timeout unless you pass one to ``run()``.
    """

    api_key: Optional[str] = field(default=None, repr=False)
    base_url: Optional[str] = None
    team_id: Optional[str] = None
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("MAXUN_API_KEY")
        self.base_url = self.base_url or os.environ.get("MAXUN_BASE_URL") or DEFAULT_BASE_URL
        self.team_id = self.team_id or os.environ.get("MAXUN_TEAM_ID") or None
        if not self.api_key:
            raise ValueError(
                "No API key. Pass api_key=... or set the MAXUN_API_KEY environment variable."
            )
        if not self.base_url.endswith("/"):
            self.base_url += "/"


# ======================
# Robot management
# ======================

@dataclass
class ScheduleConfig:
    """When a robot runs on its own.

    ``run_every`` + ``run_every_unit`` set the interval. ``at_time_start`` is the
    time of day (``"HH:MM"``) for DAYS/WEEKS/MONTHS schedules; ``start_from`` is
    the weekday for WEEKS schedules; ``day_of_month`` is for MONTHS schedules.

    ``cron_expression``, ``last_run_at`` and ``next_run_at`` are filled in by the
    server and are ignored when you send a schedule.
    """

    run_every: int
    run_every_unit: TimeUnit
    timezone: str = "UTC"
    start_from: Optional[Weekday] = None
    day_of_month: Optional[int] = None
    at_time_start: Optional[str] = None
    at_time_end: Optional[str] = None
    cron_expression: Optional[str] = None
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None


@dataclass
class WebhookConfig:
    """A URL that Maxun POSTs to when a run finishes.

    ``events`` defaults to both ``"run_completed"`` and ``"run_failed"``.
    ``retry_attempts`` (default 3), ``retry_delay`` (seconds, default 5, doubled
    on each retry) and ``timeout`` (seconds, default 30) control delivery.
    """

    url: str
    events: Optional[List[WebhookEvent]] = None
    headers: Optional[Dict[str, str]] = None  # Not supported by the server; ignored with a warning.
    retry_attempts: Optional[int] = None
    retry_delay: Optional[int] = None
    timeout: Optional[int] = None


@dataclass
class ExecutionOptions:
    """Options for a single ``robot.run()``.

    ``formats`` overrides the robot's output formats for this run only.
    ``smart_queries`` asks the LLM a question about the scraped page for this
    run only (scrape robots). ``timeout`` is in seconds; ``None`` waits until
    the run finishes.
    """

    # params, webhook and wait_for_completion are deprecated: the server never
    # used them. They stay (in their original positions) so old code still runs.
    params: Optional[Dict[str, Any]] = None
    webhook: Optional["WebhookConfig"] = None
    timeout: Optional[float] = None
    wait_for_completion: Optional[bool] = None
    formats: Optional[List[Format]] = None
    smart_queries: Optional[str] = None


# ======================
# Extract
# ======================

ExtractFields = Dict[str, str]


@dataclass
class PaginationConfig:
    """How to reach more list items. Leave pagination out entirely to let Maxun
    auto-detect it; use ``type="none"`` to only read the first page."""

    type: PaginationType
    selector: Optional[str] = None


@dataclass
class ExtractListConfig:
    """A repeated element to capture as a list. Fields inside each item are
    detected automatically. ``max_items`` defaults to 100."""

    selector: str
    pagination: Optional[PaginationConfig] = None
    max_items: Optional[int] = None


# ======================
# Crawl
# ======================

@dataclass
class CrawlConfig:
    """Which pages a crawl robot visits.

    ``mode`` keeps the crawl on the same ``"domain"``, ``"subdomain"`` or URL
    ``"path"``. ``limit`` is the maximum number of pages; ``max_depth`` is how
    many links deep to follow. ``include_paths``/``exclude_paths`` are URL
    patterns.
    """

    mode: CrawlMode = "domain"
    include_paths: Optional[List[str]] = None
    exclude_paths: Optional[List[str]] = None
    limit: int = 50
    max_depth: int = 3
    respect_robots: bool = True
    use_sitemap: bool = True
    follow_links: bool = True


@dataclass
class CrawlOptions:
    crawl_config: CrawlConfig
    name: Optional[str] = None


# ======================
# Search
# ======================

@dataclass
class SearchConfig:
    """A web search (DuckDuckGo).

    ``mode="discover"`` returns result titles, URLs and snippets only.
    ``mode="scrape"`` (the default) also opens every result and scrapes it in the
    robot's ``formats``. ``limit`` is the number of results (default 10).
    ``time_range`` restricts results to the past day/week/month/year.
    """

    query: str
    mode: SearchMode = "scrape"
    provider: Optional[SearchProvider] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    time_range: Optional[SearchTimeRange] = None


@dataclass
class SearchOptions:
    search_config: SearchConfig
    name: Optional[str] = None


# ======================
# Raw payload aliases
# ======================

Workflow = List[Dict[str, Any]]
WorkflowFile = Dict[str, Any]
RobotData = Dict[str, Any]
Run = Dict[str, Any]
RunResult = Dict[str, Any]  # raw shape; maxun.RunResult is the class in robot.py
ApiResponse = Dict[str, Any]


class ListLimitUpdate(TypedDict):
    pairIndex: int
    actionIndex: int
    argIndex: int
    limit: int


# ======================
# Errors
# ======================

class MaxunError(Exception):
    """Base class for every error the SDK raises about an API call."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.message}" if self.status_code else self.message


class AuthenticationError(MaxunError):
    """The API key is missing, invalid or not allowed to do this (401/403)."""


class NotFoundError(MaxunError):
    """The robot or run does not exist (404)."""


class ConflictError(MaxunError):
    """A robot with this name already exists with a different configuration (409)."""


class ValidationError(MaxunError):
    """The server rejected the request's input (400)."""


class RunFailedError(MaxunError):
    """The robot ran but the run failed or was aborted."""
