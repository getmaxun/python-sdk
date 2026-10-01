"""Change monitoring for crawl robots, done in the SDK.

The Maxun server compares runs for scrape and extract robots, but not for crawl
robots. For those, the SDK compares a run with the previous successful run
itself, page by page, and returns the result in the same shape the server uses
for the other robot types.

If a run already carries the server's own comparison (``_comparison`` in its
output), the SDK leaves it alone.
"""

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

COMPARABLE_FORMATS = ("text", "markdown", "html")


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def crawl_pages(crawl_output: Any) -> List[dict]:
    """Pages from a run's ``crawl`` output (a list, or a dict of lists)."""
    if isinstance(crawl_output, list):
        return [p for p in crawl_output if isinstance(p, dict)]
    if isinstance(crawl_output, dict):
        pages: List[dict] = []
        for value in crawl_output.values():
            if isinstance(value, list):
                pages.extend(p for p in value if isinstance(p, dict))
        return pages
    return []


def _page_url(page: dict) -> str:
    return str((page.get("metadata") or {}).get("url") or page.get("url") or "")


def _by_url(pages: List[dict]) -> Dict[str, dict]:
    return {_page_url(p): p for p in pages if not p.get("error")}


def _document(pages: Dict[str, dict], fmt: str) -> str:
    parts = []
    for url in sorted(pages):
        content = pages[url].get(fmt)
        if isinstance(content, str):
            parts.append(f"## {url}\n{content.rstrip()}\n")
    return "\n".join(parts)


def _formats_present(*page_sets: Dict[str, dict]) -> List[str]:
    return [
        fmt for fmt in COMPARABLE_FORMATS
        if any(isinstance(p.get(fmt), str) for pages in page_sets for p in pages.values())
    ]


def compare_crawl(previous: List[dict], current: List[dict]) -> Tuple[List[str], Dict[str, List[str]]]:
    """Return ``(changed_formats, pages)`` where pages lists added, removed and
    changed page URLs."""
    prev, cur = _by_url(previous), _by_url(current)
    formats = _formats_present(cur)
    changed_formats = [
        fmt for fmt in formats
        if _normalize(_document(prev, fmt)) != _normalize(_document(cur, fmt))
    ]
    changed_pages = [
        url for url in sorted(set(prev) & set(cur))
        if any(
            _normalize(str(prev[url].get(fmt) or "")) != _normalize(str(cur[url].get(fmt) or ""))
            for fmt in formats
        )
    ]
    pages = {
        "added": sorted(set(cur) - set(prev)),
        "removed": sorted(set(prev) - set(cur)),
        "changed": changed_pages,
    }
    return changed_formats, pages


def _line_diff(old: str, new: str) -> List[dict]:
    """Line diff in the server's format: ``[{"value", "added", "removed"}]``."""
    a, b = old.splitlines(keepends=True), new.splitlines(keepends=True)
    changes: List[dict] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            changes.append({"value": "".join(a[i1:i2]), "added": False, "removed": False})
            continue
        if tag in ("delete", "replace"):
            changes.append({"value": "".join(a[i1:i2]), "added": False, "removed": True})
        if tag in ("insert", "replace"):
            changes.append({"value": "".join(b[j1:j2]), "added": True, "removed": False})
    return changes


def crawl_diff(
    run_id: str,
    previous_run: Optional[dict],
    current_output: Any,
    format: Optional[str] = None,
) -> dict:
    """A diff dict shaped like the server's ``/runs/:id/diff`` response, plus ``pages``."""
    if previous_run is None:
        return {"runId": run_id, "previousRunId": None, "hasChanges": False,
                "changedFormats": [], "diffs": [], "pages": {"added": [], "removed": [], "changed": []}}
    prev_pages = crawl_pages((previous_run.get("serializableOutput") or {}).get("crawl"))
    cur_pages = crawl_pages(current_output)
    changed_formats, pages = compare_crawl(prev_pages, cur_pages)
    prev, cur = _by_url(prev_pages), _by_url(cur_pages)
    formats = [f for f in changed_formats if not format or f == format]
    return {
        "runId": run_id,
        "previousRunId": previous_run.get("runId"),
        "hasChanges": bool(changed_formats),
        "changedFormats": changed_formats,
        "diffs": [{"format": f, "changes": _line_diff(_document(prev, f), _document(cur, f))} for f in formats],
        "pages": pages,
    }


def previous_successful_run(runs: List[dict], run_id: str) -> Optional[dict]:
    """The successful run before ``run_id`` in a newest-first list."""
    index = next((i for i, r in enumerate(runs) if r.get("runId") == run_id), None)
    older = runs[index + 1:] if index is not None else runs
    return next((r for r in older if r.get("status") == "success" and r.get("runId") != run_id), None)
