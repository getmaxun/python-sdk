from dataclasses import dataclass
from typing import List, Optional, Literal


LLMProvider = Literal["anthropic", "openai", "ollama"]


@dataclass
class LLMConfig:
    provider: LLMProvider
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096


@dataclass
class LLMMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class LLMResponse:
    content: str
    usage: Optional[TokenUsage] = None