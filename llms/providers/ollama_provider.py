import os
from typing import List

import httpx

from ..types import LLMMessage, LLMResponse, TokenUsage
from .base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, config):
        super().__init__(config)

        self.base_url = (
            config.base_url
            or os.getenv("OLLAMA_HOST")
            or "http://localhost:11434"
        )

    async def chat(self, messages: List[LLMMessage]) -> LLMResponse:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.config.model or "llama3.1",
                        "messages": [m.__dict__ for m in messages],
                        "options": {
                            "temperature": self.config.temperature or 0.7,
                            "num_predict": self.config.max_tokens or 2048,
                        },
                    },
                )

                response.raise_for_status()
                data = response.json()

                return LLMResponse(
                    content=data["message"]["content"],
                    usage=TokenUsage(
                        prompt_tokens=data.get("prompt_eval_count", 0),
                        completion_tokens=data.get("eval_count", 0),
                        total_tokens=data.get("prompt_eval_count", 0)
                        + data.get("eval_count", 0),
                    ),
                )

        except Exception as e:
            raise RuntimeError(f"Ollama API error: {str(e)}")

    def validate_config(self):
        pass  # defaults handled automatically

    def get_provider_name(self) -> str:
        return "Ollama"