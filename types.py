from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal

# ======================
# Core Types
# ======================

RobotType = Literal["extract", "scrape", "crawl", "search"]
RobotMode = Literal["normal", "bulk"]
Format = Literal["markdown", "html", "screenshot-visible", "screenshot-fullpage"]
RunStatus = Literal["running", "queued", "success", "failed", "aborting", "aborted"]
TimeUnit = Literal["MINUTES", "HOURS", "DAYS", "WEEKS", "MONTHS"]
CrawlMode = Literal["domain", "subdomain", "path"]
LLMProvider = Literal["anthropic", "openai", "ollama"]
SearchMode = Literal["discover", "scrape"]
SearchProvider = Literal["duckduckgo"]


@dataclass
class Config:
    api_key: str
    base_url: Optional[str] = None
    team_id: Optional[str] = None


@dataclass
class ScheduleConfig:
    run_every: int
    run_every_unit: TimeUnit
    timezone: str
    start_from: Optional[str] = None  # 'SUNDAY' | 'MONDAY' | ... | 'SATURDAY'
    day_of_month: Optional[int] = None
    at_time_start: Optional[str] = None
    at_time_end: Optional[str] = None
    cron_expression: Optional[str] = None
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None


@dataclass
class WebhookConfig:
    url: str
    events: Optional[List[str]] = None
    headers: Optional[Dict[str, str]] = None


@dataclass
class ExecutionOptions:
    params: Optional[Dict[str, Any]] = None
    webhook: Optional["WebhookConfig"] = None
    timeout: Optional[int] = None
    wait_for_completion: Optional[bool] = None


# ======================
# Extract-specific Types
# ======================

ExtractFields = Dict[str, str]


@dataclass
class PaginationConfig:
    type: Literal["scrollDown", "clickNext", "clickLoadMore", "scrollUp"]
    selector: Optional[str] = None


@dataclass
class ExtractListConfig:
    selector: str
    pagination: Optional[PaginationConfig] = None
    max_items: Optional[int] = None


# ======================
# Crawl-specific Types
# ======================

@dataclass
class CrawlConfig:
    mode: CrawlMode
    include_paths: Optional[List[str]] = None
    exclude_paths: Optional[List[str]] = None
    limit: Optional[int] = None
    max_depth: Optional[int] = None
    respect_robots: Optional[bool] = None
    use_sitemap: Optional[bool] = None
    follow_links: Optional[bool] = None


@dataclass
class CrawlOptions:
    crawl_config: CrawlConfig
    name: Optional[str] = None


@dataclass
class SearchConfig:
    query: str
    mode: Optional[SearchMode] = None
    provider: Optional[SearchProvider] = None
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None


@dataclass
class SearchOptions:
    search_config: SearchConfig
    name: Optional[str] = None


# Type aliases for API payload structures (dict-based for JSON serialization)
Workflow = List[Dict[str, Any]]
WorkflowFile = Dict[str, Any]
RobotData = Dict[str, Any]
Run = Dict[str, Any]
RunResult = Dict[str, Any]
ApiResponse = Dict[str, Any]


class MaxunError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details