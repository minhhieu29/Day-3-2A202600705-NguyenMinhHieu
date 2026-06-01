"""Run resort ReAct agent: python scripts/run_agent.py \"your question\""""

import argparse
import os
import sys

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.console_utf8 import configure_utf8_console

configure_utf8_console()

from src.agent.agent import ReActAgent
from src.core.provider_factory import get_llm_from_env
from src.tools import TOOLS

DEFAULT_QUESTION = (
    "Khách phàn nàn gì về phòng và ăn sáng tại Sunrise Bay? "
    "Đưa trích dẫn cụ thể. Đề xuất 2 ưu tiên cải thiện vận hành."
)


def main() -> None:
    load_dotenv(os.path.join(ROOT, ".env"), override=True)
    parser = argparse.ArgumentParser(description="Resort review ReAct agent")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--max-steps", type=int, default=6)
    args = parser.parse_args()

    llm = get_llm_from_env()
    agent = ReActAgent(llm=llm, tools=TOOLS, max_steps=args.max_steps)
    print(f"\n--- ReAct Agent | {llm.model_name} | tools: {len(TOOLS)} ---\n")
    print(agent.run(args.question))


if __name__ == "__main__":
    main()
