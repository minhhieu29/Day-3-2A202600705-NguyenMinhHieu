import time
from typing import Any, Dict, Generator, Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from src.core.llm_provider import LLMProvider

MAX_RETRIES = 4
RETRY_BASE_SECONDS = 3


class GeminiProvider(LLMProvider):
    """Gemini API via the unified Google Gen AI SDK (google-genai)."""

    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        self.client = genai.Client(api_key=self.api_key)

    def _build_config(self, system_prompt: Optional[str]) -> Optional[types.GenerateContentConfig]:
        if not system_prompt:
            return None
        return types.GenerateContentConfig(system_instruction=system_prompt)

    @staticmethod
    def _usage_from_response(response: Any) -> Dict[str, int]:
        meta = getattr(response, "usage_metadata", None)
        if not meta:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        prompt = getattr(meta, "prompt_token_count", 0) or 0
        completion = getattr(meta, "candidates_token_count", 0) or 0
        total = getattr(meta, "total_token_count", None) or (prompt + completion)
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }

    def _call_generate(self, kwargs: Dict[str, Any]) -> Any:
        """Retry on Gemini 503 (high demand) or 429 (quota) — transient server-side errors."""
        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                return self.client.models.generate_content(**kwargs)
            except genai_errors.APIError as exc:
                last_error = exc
                code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                retryable = code in (429, 503) or "503" in str(exc) or "429" in str(exc)
                if not retryable or attempt >= MAX_RETRIES - 1:
                    raise
                wait = RETRY_BASE_SECONDS * (2**attempt)
                time.sleep(wait)
        raise last_error  # type: ignore[misc]

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        config = self._build_config(system_prompt)

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "contents": prompt,
        }
        if config is not None:
            kwargs["config"] = config

        response = self._call_generate(kwargs)

        latency_ms = int((time.time() - start_time) * 1000)
        content = response.text or ""

        return {
            "content": content,
            "usage": self._usage_from_response(response),
            "latency_ms": latency_ms,
            "provider": "google",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        config = self._build_config(system_prompt)
        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "contents": prompt,
        }
        if config is not None:
            kwargs["config"] = config

        for chunk in self.client.models.generate_content_stream(**kwargs):
            if chunk.text:
                yield chunk.text
