from typing import Any, List, Optional

from .client import Client
from .robot import Robot
from .types import Config


class Resource:
    """Shared plumbing for Scrape, Crawl, Search, Extract, Documents and Robots.

    Each can be built on its own (``Scrape(Config(...))`` or just ``Scrape()`` to
    read MAXUN_* environment variables) or reached through :class:`maxun.Maxun`,
    which shares one connection between them.
    """

    #: Robot types this resource lists. ``None`` means all robots.
    robot_types: Optional[tuple] = None

    def __init__(self, config: Optional[Config] = None, *, client: Optional[Client] = None):
        self.client = client or Client(config)

    async def close(self) -> None:
        """Close the HTTP connection. Not needed when using ``async with``."""
        await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _after_create(self, robot_data: dict, monitor: Optional[bool] = None) -> Robot:
        robot = Robot(self.client, robot_data)
        if monitor is not None and bool(monitor) != robot.is_monitoring:
            await robot.set_monitoring(bool(monitor))
        return robot

    async def list(self) -> List[Robot]:
        """Robots of this kind on your account."""
        robots = await self.client.get_robots()
        wrapped = [Robot(self.client, r) for r in robots]
        if self.robot_types is None:
            return wrapped
        return [r for r in wrapped if r.type in self.robot_types]

    async def get(self, robot_id: str) -> Robot:
        return Robot(self.client, await self.client.get_robot(robot_id))

    async def delete(self, robot_id: str) -> None:
        await self.client.delete_robot(robot_id)

    # Older names, kept so existing code keeps working.
    async def get_robots(self) -> List[Robot]:
        return await self.list()

    async def get_robot(self, robot_id: str) -> Robot:
        return await self.get(robot_id)

    async def delete_robot(self, robot_id: str) -> None:
        await self.delete(robot_id)
