from typing import Any, List, Optional

from .client import Client
from .robot import Robot
from .types import Config


async def list_robots(client: Client, types: Optional[tuple] = None) -> List[Robot]:
    """Fetch every robot once and keep those whose type is in ``types`` (all if None)."""
    records = await client.get_robots()
    robots = [Robot(client, record) for record in records]
    if not types:
        return robots
    return [robot for robot in robots if robot.type in types]


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

    async def list(self, type: Optional[str] = None) -> List[Robot]:  # noqa: A002
        """Robots of this kind on your account.

        ``maxun.scrape.list()`` is the same call as ``maxun.robots.list(type="scrape")``.
        """
        types = (type,) if type else self.robot_types
        if type and self.robot_types is not None and type not in self.robot_types:
            raise ValueError(f"{self.__class__.__name__} robots are {', '.join(self.robot_types)}, not {type}.")
        return await list_robots(self.client, types)

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
