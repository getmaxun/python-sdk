from typing import Any, Dict, List, Optional
from ..types import RobotType, RobotMode, Format


class WorkflowBuilder:
    def __init__(self, name: str, robot_type: RobotType):
        self.name = name
        self.robot_type = robot_type
        self.workflow: List[Dict[str, Any]] = []
        self.meta: Dict[str, Any] = {
            "name": name,
            "robotType": robot_type,
        }
        self.current_step: Optional[Dict[str, Any]] = None
        self._is_first_navigation = True

    def navigate(self, url: str):
        main_step = {"where": {"url": url}, "what": []}

        if self._is_first_navigation:
            about_blank_step = {
                "where": {"url": "about:blank"},
                "what": [
                    {"action": "goto", "args": [url]},
                    {"action": "waitForLoadState", "args": ["networkidle"]},
                ],
            }

            self.workflow.insert(0, main_step)
            self.workflow.append(about_blank_step)
            self._is_first_navigation = False
        else:
            self.workflow.insert(0, main_step)

        self.current_step = main_step
        return self

    def click(self, selector: str):
        return self._add_action("click", [selector])

    def type(self, selector: str, text: str, input_type: Optional[str] = None):
        args = [selector, text, input_type] if input_type else [selector, text]
        return self._add_action("type", args)

    def wait_for(self, selector: str, timeout: Optional[int] = None):
        return self._add_action(
            "waitForSelector",
            [selector, {"timeout": timeout or 30000}],
        )

    def wait(self, milliseconds: int):
        return self._add_action("waitForTimeout", [milliseconds])

    def capture_screenshot(self, name: Optional[str] = None, options: Optional[dict] = None):
        if options:
            screenshot_args = {
                "type": options.get("type", "png"),
                "caret": options.get("caret", "hide"),
                "scale": options.get("scale", "device"),
                "timeout": options.get("timeout", 30000),
                "fullPage": options.get("fullPage", True),
                "animations": options.get("animations", "allow"),
            }
            if options.get("quality") is not None:
                screenshot_args["quality"] = options["quality"]
        else:
            screenshot_args = {
                "type": "png",
                "caret": "hide",
                "scale": "device",
                "timeout": 30000,
                "fullPage": True,
                "animations": "allow",
            }

        self._add_action("screenshot", [screenshot_args], name)
        return self

    def scroll(self, direction: str, distance: Optional[int] = None):
        return self._add_action("scroll", [{"direction": direction, "distance": distance}])

    def set_cookies(self, cookies: List[Dict[str, str]]):
        if self.current_step:
            self.current_step["where"]["cookies"] = cookies
        return self

    def mode(self, mode: RobotMode):
        self.meta["mode"] = mode
        return self

    def format(self, formats: List[Format]):
        self.meta["formats"] = formats
        return self

    def _add_action(self, action: str, args: list, name: Optional[str] = None):
        action_obj = {"action": action, "args": args}
        if name:
            action_obj["name"] = name

        if not self.current_step:
            step = {"where": {}, "what": [action_obj]}
            self.workflow.insert(0, step)
            self.current_step = step
        else:
            self.current_step["what"].append(action_obj)

        return self

    def get_workflow_array(self):
        return self.workflow

    def get_workflow(self):
        return {
            "meta": self.meta,
            "workflow": self.workflow,
        }

    def get_meta(self):
        return self.meta