"""
Smoke-test cloud LLM providers configured in .env.

  python scripts/test_provider.py           # uses DEFAULT_PROVIDER
  python scripts/test_provider.py openai
  python scripts/test_provider.py google
  python scripts/test_provider.py mimo
"""
import argparse
import os
import sys
from typing import Optional

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.provider_factory import get_llm_from_env
from src.telemetry.metrics import tracker


def run_test(provider: Optional[str] = None) -> None:
    env_path = os.path.join(ROOT, ".env")
    if not os.path.isfile(env_path):
        raise ValueError(
            f"No .env file at {env_path}. Run: copy .env.example .env then add your API keys."
        )
    load_dotenv(env_path, override=True)
    print(f"Loaded: {env_path}")

    llm = get_llm_from_env(provider)
    label = provider or os.getenv("DEFAULT_PROVIDER", "openai")
    prompt = "Reply with exactly: OK"

    print(f"--- Provider: {label} | Model: {llm.model_name} ---")
    result = llm.generate(prompt)
    print(f"Response: {result['content'][:200]}")
    print(f"Latency: {result['latency_ms']} ms")
    print(f"Tokens: {result['usage']}")

    tracker.track_request(
        provider=result.get("provider", label),
        model=llm.model_name,
        usage=result["usage"],
        latency_ms=result["latency_ms"],
    )
    print("Telemetry logged (see logs/ folder).")
    print("OK — provider is working.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test LLM provider from .env")
    parser.add_argument(
        "provider",
        nargs="?",
        choices=["openai", "google", "mimo"],
        help="Override DEFAULT_PROVIDER for this run",
    )
    args = parser.parse_args()
    try:
        run_test(args.provider)
    except ValueError as e:
        print(f"Setup error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"API error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
