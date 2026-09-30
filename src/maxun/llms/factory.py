from .types import LLMConfig


def create_llm_provider(config: LLMConfig):
    if config.provider == "openai":
        from .providers.openai_provider import OpenAIProvider
        return OpenAIProvider(config)
    elif config.provider == "anthropic":
        from .providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(config)
    elif config.provider == "ollama":
        from .providers.ollama_provider import OllamaProvider
        return OllamaProvider(config)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")