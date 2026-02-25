import os
from typing import List

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None  # type: ignore[assignment,misc]

from ..types import LLMMessage, LLMResponse, TokenUsage
from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, config):
        if AsyncAnthropic is None:
            raise ImportError(
                "The 'anthropic' package is required to use AnthropicProvider. "
                "Install it with: pip install anthropic"
            )
        super().__init__(config)

        self.client = AsyncAnthropic(
            api_key=config.api_key or os.getenv("ANTHROPIC_API_KEY")
        )

    async def chat(self, messages: List[LLMMessage]) -> LLMResponse:
        try:
            system_message = next((m for m in messages if m.role == "system"), None)
            user_messages = [m for m in messages if m.role != "system"]

            response = await self.client.messages.create(
                model=self.config.model or "claude-3-5-sonnet-20241022",
                max_tokens=self.config.max_tokens or 4096,
                temperature=self.config.temperature or 0.7,
                system=system_message.content if system_message else None,
                messages=[
                    {"role": m.role, "content": m.content}
                    for m in user_messages
                ],
            )

            text_block = next(
                (c for c in response.content if c.type == "text"), None
            )

            return LLMResponse(
                content=text_block.text if text_block else "",
                usage=TokenUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens
                    + response.usage.output_tokens,
                )
                if response.usage
                else None,
            )

        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")

    def validate_config(self):
        if not (self.config.api_key or os.getenv("ANTHROPIC_API_KEY")):
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY or provide api_key."
            )

    def get_provider_name(self) -> str:
        return "Anthropic"