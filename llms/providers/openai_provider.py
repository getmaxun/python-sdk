import os
from typing import List

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment,misc]

from ..types import LLMMessage, LLMResponse, TokenUsage
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, config):
        if AsyncOpenAI is None:
            raise ImportError(
                "The 'openai' package is required to use OpenAIProvider. "
                "Install it with: pip install openai"
            )
        super().__init__(config)

        self.client = AsyncOpenAI(
            api_key=config.api_key or os.getenv("OPENAI_API_KEY"),
            base_url=config.base_url,
        )

    async def chat(self, messages: List[LLMMessage]) -> LLMResponse:
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model or "gpt-4o-mini",
                messages=[m.__dict__ for m in messages],
                temperature=self.config.temperature or 0.7,
                max_tokens=self.config.max_tokens or 4096,
            )

            choice = response.choices[0]

            return LLMResponse(
                content=choice.message.content or "",
                usage=TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens or 0,
                    completion_tokens=response.usage.completion_tokens or 0,
                    total_tokens=response.usage.total_tokens or 0,
                )
                if response.usage
                else None,
            )

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    def validate_config(self):
        if not (self.config.api_key or os.getenv("OPENAI_API_KEY")):
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY or provide api_key."
            )

    def get_provider_name(self) -> str:
        return "OpenAI"