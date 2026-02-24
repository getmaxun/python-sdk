from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal


RobotType = Literal["extract", "scrape", "crawl", "search"]
RobotMode = Literal["normal", "bulk"]
Format = Literal["markdown", "html", "screenshot-visible", "screenshot-fullpage"]
RunStatus = Literal["running", "queued", "success", "failed", "aborting", "aborted"]
TimeUnit = Literal["MINUTES", "HOURS", "DAYS", "WEEKS", "MONTHS"]
CrawlMode = Literal["domain", "subdomain", "path"]
LLMProvider = Literal["anthropic", "openai", "ollama"]


@dataclass
class Config:
    api_key: str
    base_url: Optional[str] = None
    team_id: Optional[str] = None


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
class SearchConfig:
    query: str
    mode: Optional[str] = None
    provider: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None


class MaxunError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details