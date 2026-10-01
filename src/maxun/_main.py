"""The main entry point: ``Maxun`` (async) and ``MaxunSync`` (blocking)."""

import asyncio
import functools
import inspect
import threading
from typing import Any, List, Optional

from ._resource import Resource
from .builders.extract_builder import ExtractBuilder
from .client import Client
from .crawl import Crawl
from .documents import Documents
from .extract import Extract
from .robot import Robot
from .scrape import Scrape
from .search import Search
from .types import Config, NotFoundError


class Robots(Resource):
    """Every robot on your account, whatever its type."""

    robot_types = None

    async def list(self, type: Optional[str] = None) -> List[Robot]:  # noqa: A002
        """All robots, or only those of one ``type`` (extract, scrape, crawl,
        search, doc-extract, doc-parse)."""
        return await super().list(type)

    async def find(self, name: str) -> Robot:
        """The robot with this exact name."""
        for robot in await self.list():
            if robot.name.strip() == name.strip():
                return robot
        raise NotFoundError(f'No robot named "{name}"', 404)


class Maxun:
    """One connection to Maxun with every feature on it::

        async with Maxun() as maxun:          # reads MAXUN_API_KEY / MAXUN_BASE_URL
            robot = await maxun.scrape.create("Home page", "https://example.com")
            result = await robot.run()
            print(result.markdown)

    Arguments left out are read from ``MAXUN_API_KEY``, ``MAXUN_BASE_URL`` and
    ``MAXUN_TEAM_ID``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        team_id: Optional[str] = None,
        timeout: float = 30.0,
        *,
        config: Optional[Config] = None,
    ):
        self.config = config or Config(api_key=api_key, base_url=base_url, team_id=team_id, timeout=timeout)
        self.client = Client(self.config)
        self.scrape = Scrape(client=self.client)
        self.crawl = Crawl(client=self.client)
        self.search = Search(client=self.client)
        self.extract = Extract(client=self.client)
        self.documents = Documents(client=self.client)
        self.robots = Robots(client=self.client)

    async def status(self) -> dict:
        """Account info for this API key."""
        return await self.client.get_status()

    async def close(self) -> None:
        await self.client.close()

    async def __aenter__(self) -> "Maxun":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# Blocking wrapper
# ---------------------------------------------------------------------------

class _LoopThread:
    """A private event loop on a background thread, so blocking code can call
    the async SDK (and it works inside Jupyter, where a loop is already running)."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="maxun-sync", daemon=True)
        self.thread.start()

    def run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

    def stop(self) -> None:
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=5)
        if not self.loop.is_running() and not self.loop.is_closed():
            self.loop.close()


_WRAP_TYPES = (Robot, Resource, ExtractBuilder)


class _SyncProxy:
    """Wraps an SDK object so its async methods block and return wrapped objects."""

    def __init__(self, target: Any, runner: _LoopThread):
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_runner", runner)

    def _wrap(self, value: Any) -> Any:
        return _wrap(value, self._runner)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._target, name)
        if inspect.iscoroutinefunction(attr):
            @functools.wraps(attr)
            def blocking(*args: Any, **kwargs: Any) -> Any:
                return self._wrap(self._runner.run(attr(*args, **kwargs)))
            return blocking
        if callable(attr) and not isinstance(attr, type):
            @functools.wraps(attr)
            def plain(*args: Any, **kwargs: Any) -> Any:
                return self._wrap(attr(*args, **kwargs))
            return plain
        return self._wrap(attr)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        result = self._target(*args, **kwargs)
        if inspect.isawaitable(result) and not isinstance(result, _WRAP_TYPES):
            result = self._runner.run(result)
        return self._wrap(result)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._target, name, value)

    def __repr__(self) -> str:
        return repr(self._target)


class _SyncRobot(dict):
    """A robot for MaxunSync: the same plain dict of id, name and type as
    :class:`Robot`, with methods that block instead of returning coroutines."""

    def __init__(self, target: Robot, runner: _LoopThread):
        super().__init__(target)
        self.__dict__["_proxy"] = _SyncProxy(target, runner)
        self.__dict__["_target"] = target

    def _refresh(self) -> None:
        dict.clear(self)
        dict.update(self, self._target)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._proxy, name)
        if callable(attr):
            @functools.wraps(attr)
            def call(*args: Any, **kwargs: Any) -> Any:
                try:
                    return attr(*args, **kwargs)
                finally:
                    self._refresh()
            return call
        return attr

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(self._target)


def _wrap(value: Any, runner: _LoopThread) -> Any:
    if isinstance(value, Robot):
        return _SyncRobot(value, runner)
    if isinstance(value, _WRAP_TYPES):
        return _SyncProxy(value, runner)
    if isinstance(value, list) and value and all(isinstance(v, Robot) for v in value):
        return [_SyncRobot(v, runner) for v in value]
    return value


class MaxunSync:
    """Same API as :class:`Maxun`, without ``await``::

        with MaxunSync() as maxun:
            robot = maxun.scrape.create("Home page", "https://example.com")
            print(robot.run().markdown)

    Selector robots finish with ``.build()``:
    ``maxun.extract.create("x").navigate(url).capture_text({...}).build()``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        team_id: Optional[str] = None,
        timeout: float = 30.0,
        *,
        config: Optional[Config] = None,
    ):
        self._runner = _LoopThread()
        try:
            # The async client must be created on the loop that will use it.
            self._async = self._runner.run(
                _create(api_key=api_key, base_url=base_url, team_id=team_id, timeout=timeout, config=config)
            )
        except BaseException:
            self._runner.stop()
            raise
        for name in ("scrape", "crawl", "search", "extract", "documents", "robots"):
            setattr(self, name, _SyncProxy(getattr(self._async, name), self._runner))
        self.config = self._async.config

    def status(self) -> dict:
        return self._runner.run(self._async.status())

    def close(self) -> None:
        try:
            self._runner.run(self._async.close())
        finally:
            self._runner.stop()

    def __enter__(self) -> "MaxunSync":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


async def _create(**kwargs: Any) -> Maxun:
    return Maxun(**kwargs)
