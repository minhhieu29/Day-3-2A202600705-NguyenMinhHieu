"""Run resort baseline chatbot: python scripts/run_chatbot.py \"your question\""""

import argparse
import os
import sys

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.console_utf8 import configure_utf8_console

configure_utf8_console()

from src.chatbot import ResortChatbot
from src.core.provider_factory import get_llm_from_env

DEFAULT_QUESTION = (
    "Khách phàn nàn gì về phòng và ăn sáng tại Sunrise Bay? "
    "Đề xuất ưu tiên cải thiện."
)


def main() -> None:
    load_dotenv(os.path.join(ROOT, ".env"), override=True)
    parser = argparse.ArgumentParser(description="Resort review chatbot (no tools)")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    args = parser.parse_args()

    llm = get_llm_from_env()
    bot = ResortChatbot(llm)
    print(f"\n--- Chatbot | {llm.model_name} ---\n")
    print(bot.run(args.question))


if __name__ == "__main__":
    main()
