from typing import Any, Dict, List, Optional

from .._utils import warn
from ..types import Format, RobotMode, RobotType


class WorkflowBuilder:
    """Chainable description of what a robot does in the browser.

    Steps are stored in Maxun's workflow format, where the list runs in
    reverse: the first page visited is last in ``self.workflow``.
    """

    def __init__(self, name: str, robot_type: RobotType):
        self.name = name
        self.robot_type = robot_type
        self.workflow: List[Dict[str, Any]] = []
        self.meta: Dict[str, Any] = {"name": name, "type": robot_type}
        self.current_step: Optional[Dict[str, Any]] = None
        self._is_first_navigation = True

    # ---------- navigation & interaction ----------

    def navigate(self, url: str):
        """Open a page. Every robot starts with this."""
        main_step = {"where": {"url": url}, "what": []}

        if self._is_first_navigation:
            self.workflow.append({
                "where": {"url": "about:blank"},
                "what": [
                    {"action": "goto", "args": [url]},
                    {"action": "waitForLoadState", "args": ["networkidle"]},
                ],
            })
            self._is_first_navigation = False

        self.workflow.insert(0, main_step)
        self.current_step = main_step
        return self

    def click(self, selector: str):
        return self._add_action("click", [selector])

    def type(self, selector: str, text: str, input_type: Optional[str] = None):
        """Type into an input. The text is stored encrypted on the server.
        ``input_type`` (e.g. ``"password"``) is detected when left out."""
        args = [selector, text, input_type] if input_type else [selector, text]
        return self._add_action("type", args)

    def wait_for(self, selector: str, timeout: Optional[int] = None):
        """Wait for an element to appear. ``timeout`` is in milliseconds (default 30000)."""
        return self._add_action("waitForSelector", [selector, {"timeout": timeout or 30000}])

    def wait(self, milliseconds: int):
        return self._add_action("waitForTimeout", [milliseconds])

    def scroll(self, pages: Any = 1, distance: Optional[int] = None):
        """Scroll down by ``pages`` screen heights (default 1)."""
        if isinstance(pages, str):
            # Old signature was scroll(direction, distance); it never worked
            # because the browser only supports scrolling down by pages.
            warn("scroll(direction, distance) is replaced by scroll(pages); scrolling down one page.")
            pages = 1
        return self._add_action("scroll", [int(pages)])

    def capture_screenshot(
        self,
        name: Optional[str] = None,
        options: Optional[dict] = None,
        *,
        full_page: Optional[bool] = None,
    ):
        """Take a screenshot (full page by default). Screenshots come back in
        ``result.screenshots``."""
        options = dict(options or {})
        if full_page is not None:
            options["fullPage"] = full_page
        screenshot_args = {
            "type": options.get("type", "png"),
            "caret": options.get("caret", "hide"),
            "scale": options.get("scale", "device"),
            "timeout": options.get("timeout", 30000),
            "fullPage": options.get("fullPage", options.get("full_page", True)),
            "animations": options.get("animations", "allow"),
        }
        if options.get("quality") is not None:
            screenshot_args["quality"] = options["quality"]
        return self._add_action("screenshot", [screenshot_args], name)

    def set_cookies(self, cookies: List[Dict[str, str]]):
        """Not supported: Maxun robots cannot set cookies. Kept so old code runs."""
        warn(
            "set_cookies() is not supported by Maxun and has no effect. "
            "(It used to add a page condition that could stop the step from running.)"
        )
        return self

    # ---------- robot settings ----------

    def monitor_changes(self, enabled: bool = True):
        """Compare each successful run with the previous successful run."""
        self.meta["monitor"] = enabled
        return self

    def format(self, formats: List[Format]):
        """Also capture these page formats on every run."""
        self.meta["formats"] = formats
        return self

    def mode(self, mode: RobotMode):
        """Deprecated: the server ignores robot mode."""
        warn("mode() has no effect; the Maxun server does not use a robot mode.")
        return self

    # ---------- internals ----------

    def _add_action(self, action: str, args: list, name: Optional[str] = None):
        action_obj: Dict[str, Any] = {"action": action, "args": args}
        if name:
            action_obj["name"] = name

        if not self.current_step:
            raise ValueError(f"Call navigate(url) before {action}().")
        self.current_step["what"].append(action_obj)
        return self

    def get_workflow_array(self):
        return self.workflow

    def get_workflow(self):
        return {"meta": dict(self.meta), "workflow": self.workflow}

    def get_meta(self):
        return self.meta
