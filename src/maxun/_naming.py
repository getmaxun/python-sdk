"""Automatic robot names.

When you don't name a robot, the SDK names it after what it does plus a short
fingerprint of its settings, e.g. ``Scrape: maxun.dev/pricing [3f2a1c]``.

The same call always produces the same name, so running a script twice reuses
the robot instead of creating a duplicate. Different settings give a different
fingerprint, so they never collide with an existing robot. The Node SDK uses the
same scheme, so both produce the same name for the same settings.
"""

import hashlib
import json
import re
from typing import Any

_SECRET_KEYS = {"llmApiKey"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def fingerprint(settings: Any) -> str:
    if isinstance(settings, dict):
        settings = {k: v for k, v in settings.items() if k not in _SECRET_KEYS and v is not None}
    return hashlib.sha1(canonical_json(settings).encode("utf-8")).hexdigest()[:6]


def describe_url(url: str, limit: int = 60) -> str:
    text = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url.strip(), flags=re.I)
    text = re.sub(r"^www\.", "", text).rstrip("/")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def shorten(text: str, limit: int = 50) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def auto_name(kind: str, subject: str, settings: Any) -> str:
    return f"{kind}: {subject} [{fingerprint(settings)}]"


def check_url(url: Any, call: str) -> str:
    """Catch the common mistake of passing a robot name where the URL goes."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"{call} needs a URL first, e.g. {call.split('(')[0]}('https://example.com').")
    url = url.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, flags=re.I) and (" " in url or "." not in url):
        raise ValueError(
            f"{call} takes the URL first, but got {url!r}. Pass the robot name as name=..."
        )
    return url
