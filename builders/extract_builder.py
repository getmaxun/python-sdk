from typing import Dict, Optional
from .workflow_builder import WorkflowBuilder


class ExtractBuilder(WorkflowBuilder):
    def __init__(self, name: str):
        super().__init__(name, "extract")
        self._extractor = None

    def set_extractor(self, extractor):
        self._extractor = extractor
        return self

    def capture_text(self, fields: Dict[str, str], name: Optional[str] = None):
        return self._add_action("scrapeSchema", [fields], name)

    def capture_list(self, config: dict, name: Optional[str] = None):
        scrape_list_config = {
            "itemSelector": config["selector"],
            "maxItems": config.get("maxItems", 100),
        }

        if config.get("pagination"):
            scrape_list_config["pagination"] = {
                "type": config["pagination"]["type"],
                "selector": config["pagination"].get("selector"),
            }

        return self._add_action("scrapeList", [scrape_list_config], name)

    # Make builder awaitable
    def __await__(self):
        if not self._extractor:
            raise RuntimeError(
                "Builder not properly initialized. Use extractor.create()."
            )
        return self._extractor.build(self).__await__()