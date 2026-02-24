from typing import Dict, Optional, Union
from .workflow_builder import WorkflowBuilder
from ..types import ExtractFields, ExtractListConfig


class ExtractBuilder(WorkflowBuilder):
    def __init__(self, name: str):
        super().__init__(name, "extract")
        self._extractor = None

    def set_extractor(self, extractor):
        self._extractor = extractor
        return self

    def capture_text(self, fields: ExtractFields, name: Optional[str] = None):
        return self._add_action("scrapeSchema", [fields], name)

    def capture_list(self, config: Union[ExtractListConfig, dict], name: Optional[str] = None):
        # Support both ExtractListConfig dataclass and plain dict
        if hasattr(config, "selector"):
            selector = config.selector
            max_items = config.max_items if config.max_items is not None else 100
            pagination = config.pagination
        else:
            selector = config["selector"]
            max_items = config.get("maxItems", 100)
            pagination = config.get("pagination")

        scrape_list_config = {
            "itemSelector": selector,
            "maxItems": max_items,
        }

        if pagination is not None:
            if hasattr(pagination, "type"):
                scrape_list_config["pagination"] = {
                    "type": pagination.type,
                    "selector": pagination.selector or None,
                }
            else:
                scrape_list_config["pagination"] = {
                    "type": pagination["type"],
                    "selector": pagination.get("selector") or None,
                }

        return self._add_action("scrapeList", [scrape_list_config], name)

    # Make builder awaitable
    def __await__(self):
        if not self._extractor:
            raise RuntimeError(
                "Builder not properly initialized. Use extractor.create()."
            )
        return self._extractor.build(self).__await__()
