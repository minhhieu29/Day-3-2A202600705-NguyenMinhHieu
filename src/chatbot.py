"""Baseline chatbot: single LLM call, no tools (for comparison with ReAct agent)."""

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

RESORT_SYSTEM_PROMPT = """You are a hospitality analyst for Sunrise Bay Resort.
Answer guest-review questions using general knowledge only.
You do NOT have access to review databases or tools.
Be honest if you must estimate; mention uncertainty.
Keep answers concise and actionable.

LANGUAGE: Always respond entirely in Vietnamese (tiếng Việt), regardless of the question language."""


class ResortChatbot:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, user_input: str) -> str:
        logger.log_event("CHATBOT_START", {"input": user_input, "model": self.llm.model_name})
        result = self.llm.generate(user_input, system_prompt=RESORT_SYSTEM_PROMPT)
        tracker.track_request(
            provider=result.get("provider", "unknown"),
            model=self.llm.model_name,
            usage=result.get("usage", {}),
            latency_ms=result.get("latency_ms", 0),
        )
        content = (result.get("content") or "").strip()
        logger.log_event("CHATBOT_END", {"output_preview": content[:500]})
        return content
