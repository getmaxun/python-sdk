from abc import ABC, abstractmethod
from typing import List

from ..types import LLMConfig, LLMMessage, LLMResponse


class BaseLLMProvider(ABC):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.validate_config()

    @abstractmethod
    async def chat(self, messages: List[LLMMessage]) -> LLMResponse:
        pass

    @abstractmethod
    def validate_config(self) -> None:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    def create_system_message(self, content: str) -> LLMMessage:
        return LLMMessage(role="system", content=content)

    def create_user_message(self, content: str) -> LLMMessage:
        return LLMMessage(role="user", content=content)