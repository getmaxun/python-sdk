from typing import Optional

from .types import LLMProvider


def build_llm_payload(
    llm_provider: Optional[LLMProvider] = None,
    llm_model: Optional[str] = None,
    llm_api_key: Optional[str] = None,
    llm_base_url: Optional[str] = None,
) -> dict:
    """Returns only the LLM options that were explicitly supplied.

    All-or-nothing: omit every option to use the platform's own models (the only
    thing Maxun Cloud accepts), or supply a complete configuration for a
    self-hosted instance. A partial configuration raises here rather than at the
    server, so the error names the missing field immediately.

    ``llm_model`` is optional: self-hosted Maxun applies that provider's default
    when it is omitted, so robots created before model selection existed keep
    working without a migration.
    """
    provider = (llm_provider or "").strip()
    model = (llm_model or "").strip()
    api_key = (llm_api_key or "").strip()
    base_url = (llm_base_url or "").strip()

    if model and not provider:
        raise ValueError("llm_provider is required when llm_model is set.")
    if provider and provider != "ollama" and not api_key:
        raise ValueError(f'llm_api_key is required for provider "{provider}".')

    payload = {
        "llmProvider": provider,
        "llmModel": model,
        "llmApiKey": api_key,
        "llmBaseUrl": base_url,
    }
    return {key: value for key, value in payload.items() if value}
