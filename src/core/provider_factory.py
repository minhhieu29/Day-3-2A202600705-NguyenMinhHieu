import os
from typing import Optional

from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.core.mimo_provider import MimoProvider


def get_llm_from_env(provider: Optional[str] = None) -> LLMProvider:
    """
    Build an LLM provider from .env (DEFAULT_PROVIDER, DEFAULT_MODEL, API keys).
    provider: override env — 'openai' | 'google' | 'gemini' | 'mimo'
    """
    name = (provider or os.getenv("DEFAULT_PROVIDER", "openai")).strip().lower()
    model = os.getenv("DEFAULT_MODEL")

    if name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise ValueError(
                "OPENAI_API_KEY missing or still placeholder in .env (not .env.example). "
                "Get a key: https://platform.openai.com/api-keys"
            )
        return OpenAIProvider(
            model_name=model or "gpt-4o",
            api_key=api_key,
        )

    if name == "mimo":
        api_key = os.getenv("MIMO_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise ValueError(
                "MIMO_API_KEY missing or still placeholder in .env. "
                "Set MIMO_API_KEY and DEFAULT_PROVIDER=mimo"
            )
        return MimoProvider(
            model_name=model or "mimo-v2.5-pro",
            api_key=api_key,
        )

    if name in ("google", "gemini"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise ValueError(
                "GEMINI_API_KEY missing or still placeholder in .env (not .env.example). "
                "Get a key: https://aistudio.google.com/apikey"
            )
        return GeminiProvider(
            model_name=model or "gemini-2.5-flash",
            api_key=api_key,
        )

    if name == "local":
        raise ValueError(
            "Local provider needs llama-cpp-python and a GGUF model. "
            "Use DEFAULT_PROVIDER=openai, google, or mimo for this lab."
        )

    raise ValueError(
        f"Unknown DEFAULT_PROVIDER={name!r}. Use 'openai', 'google', or 'mimo'."
    )
