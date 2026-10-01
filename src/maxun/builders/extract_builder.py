from typing import Any, Mapping, Optional, Union

from ..types import ExtractFields, ExtractListConfig
from .workflow_builder import WorkflowBuilder


def _read(config: Any, *names: str) -> Any:
    for name in names:
        value = config.get(name) if isinstance(config, Mapping) else getattr(config, name, None)
        if value is not None:
            return value
    return None


class ExtractBuilder(WorkflowBuilder):
    """Builds a selector-based extraction robot. Finish with ``await builder.build()``
    (or ``await builder``)."""

    def __init__(self, name: Optional[str] = None):
        super().__init__(name, "extract")
        self._extractor = None

    def set_extractor(self, extractor):
        self._extractor = extractor
        return self

    def capture_text(self, fields: ExtractFields, name: Optional[str] = None):
        """Capture single values: ``{"Title": "h1", "Price": ".price"}`` (field name -> selector).
        Results are in ``result.text_data``."""
        if not fields:
            raise ValueError("capture_text() needs at least one {field_name: selector} pair")
        return self._add_action("scrapeSchema", [dict(fields)], name)

    def capture_list(self, config: Union[ExtractListConfig, dict], name: Optional[str] = None):
        """Capture a repeated element as a list. Fields inside each item are
        detected automatically. Results are in ``result.list_data``.

        ``config``: ``selector`` (required), ``max_items`` (default 100) and
        ``pagination`` (``{"type": "clickNext", "selector": "a.next"}``; leave out
        to auto-detect, or use type ``"none"`` to stay on the first page).
        """
        selector = _read(config, "selector", "itemSelector")
        if not selector:
            raise ValueError("capture_list() needs a selector for the repeated item")
        max_items = _read(config, "max_items", "maxItems", "limit") or 100

        scrape_list_config = {"itemSelector": selector, "maxItems": max_items}

        pagination = _read(config, "pagination")
        if pagination is not None:
            scrape_list_config["pagination"] = {
                "type": _read(pagination, "type"),
                "selector": _read(pagination, "selector") or None,
            }

        return self._add_action("scrapeList", [scrape_list_config], name)

    async def build(self):
        """Save this robot on Maxun and return it."""
        if not self._extractor:
            raise RuntimeError("Builder not properly initialized. Use extract.create(name).")
        return await self._extractor.build(self)

    def __await__(self):
        return self.build().__await__()
