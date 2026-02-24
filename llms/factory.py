from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.ollama_provider import OllamaProvider
from .types import LLMConfig


def create_llm_provider(config: LLMConfig):
    if config.provider == "openai":
        return OpenAIProvider(config)
    elif config.provider == "anthropic":
        return AnthropicProvider(config)
    elif config.provider == "ollama":
        return OllamaProvider(config)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")