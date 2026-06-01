import os
from typing import Optional

from src.core.openai_provider import OpenAIProvider

DEFAULT_MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"


class MimoProvider(OpenAIProvider):
    """Xiaomi MiMo API (OpenAI-compatible chat completions)."""

    def __init__(
        self,
        model_name: str = "mimo-v2.5-pro",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or os.getenv("MIMO_BASE_URL", DEFAULT_MIMO_BASE_URL),
            provider_label="mimo",
        )
