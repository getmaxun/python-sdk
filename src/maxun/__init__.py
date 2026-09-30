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
