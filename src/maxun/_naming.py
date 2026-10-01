"""Argument checks shared by ``maxun.scrape(...)``, ``maxun.crawl(...)`` and friends."""

import re
from typing import Any, Optional

_URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)


def looks_like_url(value: Any) -> bool:
    return isinstance(value, str) and bool(_URL.match(value.strip()))


def check_name(name: Any, call: str) -> str:
    """Every robot needs a name; it is what Maxun shows for it."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{call} needs a robot name first, e.g. {call.split('(')[0]}('Pricing page', ...).")
    return name.strip()


def check_url(url: Any, call: str, name: Optional[str] = None) -> str:
    if url is None and looks_like_url(name):
        raise TypeError(f"{call} takes the robot name first, then the URL, e.g. {call.split('(')[0]}('My robot', {name!r}).")
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"{call} needs a URL, e.g. {call.split('(')[0]}('My robot', 'https://example.com').")
    url = url.strip()
    if not _URL.match(url) and (" " in url or "." not in url):
        raise ValueError(f"{call} expected a URL as its second argument, but got {url!r}.")
    return url


def check_no_extra(args: tuple, call: str) -> None:
    if args:
        raise TypeError(f"{call} takes the settings as keyword arguments, e.g. formats=[...].")
