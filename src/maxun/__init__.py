"""
Maxun SDK - turn any website (or document) into an API.

Start here::

    from maxun import Maxun          # async
    from maxun import MaxunSync      # blocking
"""

from ._main import Maxun, MaxunSync, Robots
from .client import Client
from .crawl import Crawl
from .documents import Documents
from .extract import Extract
from .robot import Robot, RunResult
from .scrape import Scrape
from .search import Search
from .builders import ExtractBuilder, WorkflowBuilder
from .types import *  # noqa: F401,F403  (types.__all__ controls what is exported)
from .types import __all__ as _types_all

# LLM provider helpers (optional extras). Not needed for any robot feature:
# Maxun runs the LLM on the server.
from .llms import (
    create_llm_provider,
    BaseLLMProvider,
    AnthropicProvider,
    OpenAIProvider,
    OllamaProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
)

__version__ = "0.1.0"

__all__ = [
    "Maxun", "MaxunSync", "Robots", "Client", "Crawl", "Documents", "Extract",
    "Robot", "RunResult", "Scrape", "Search", "ExtractBuilder", "WorkflowBuilder",
    "create_llm_provider", "BaseLLMProvider", "AnthropicProvider", "OpenAIProvider",
    "OllamaProvider", "LLMConfig", "LLMMessage", "LLMResponse",
    *[name for name in _types_all if name not in ("RunResult",)],
]


def __getattr__(name: str):
    from . import types as _types

    if name in _types.DEPRECATED_CLASSES:
        import warnings

        warnings.warn(
            f"maxun.{name} is deprecated: pass plain keyword arguments instead "
            "(e.g. robot.schedule(run_every=6, run_every_unit='HOURS'), "
            "robot.add_webhook(url, events=[...]), maxun.crawl(name, url, limit=...)).",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(_types, name)
    raise AttributeError(f"module 'maxun' has no attribute {name!r}")
