"""
Run resort test cases: Chatbot vs Agent, print metrics for group report.

Usage: python scripts/run_evaluation.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.console_utf8 import configure_utf8_console

configure_utf8_console()

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from src.agent.agent import ReActAgent
from src.chatbot import ResortChatbot
from src.core.provider_factory import get_llm_from_env
from src.tools import TOOLS
from src.telemetry.metrics import tracker


def load_cases() -> list[str]:
    path = ROOT / "tests" / "test_cases_resort.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def aggregate_metrics(start: int) -> dict:
    chunk = tracker.session_metrics[start:]
    if not chunk:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_estimate": 0.0,
            "llm_calls": 0,
            "llm_latency_ms": 0,
        }
    return {
        "prompt_tokens": sum(m["prompt_tokens"] for m in chunk),
        "completion_tokens": sum(m["completion_tokens"] for m in chunk),
        "total_tokens": sum(m["total_tokens"] for m in chunk),
        "cost_estimate": round(sum(m["cost_estimate"] for m in chunk), 6),
        "llm_calls": len(chunk),
        "llm_latency_ms": sum(m["latency_ms"] for m in chunk),
    }


NO_DATA_PATTERNS = re.compile(
    r"không (có quyền|truy cập|thể truy cập)|do not have access|không có (cơ sở|database|dữ liệu)",
    re.IGNORECASE,
)
GROUNDED_PATTERNS = re.compile(
    r'["\'].{12,}["\']|TripAdvisor|Booking|Google|Agoda|room 302|breakfast|check-in|phòng|ăn sáng',
    re.IGNORECASE,
)


def score_chatbot(answer: str) -> bool:
    if len(answer) < 80:
        return False
    if NO_DATA_PATTERNS.search(answer):
        return False
    return bool(GROUNDED_PATTERNS.search(answer))


def score_agent(answer: str, tool_calls: int) -> bool:
    if tool_calls < 1:
        return False
    if len(answer) < 80:
        return False
    return bool(GROUNDED_PATTERNS.search(answer))


def main() -> None:
    cases = load_cases()
    llm = get_llm_from_env()
    results = []

    for i, question in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] {question[:60]}...")

        mark_cb = len(tracker.session_metrics)
        t0 = time.time()
        cb_answer = ResortChatbot(llm).run(question)
        cb_ms = int((time.time() - t0) * 1000)
        cb_m = aggregate_metrics(mark_cb)
        cb_m["latency_ms"] = cb_ms

        mark_ag = len(tracker.session_metrics)
        t0 = time.time()
        agent = ReActAgent(llm=llm, tools=TOOLS, max_steps=6)
        ag_answer = agent.run(question)
        ag_ms = int((time.time() - t0) * 1000)
        tool_calls = sum(1 for h in agent.history if h.startswith("Action:"))
        ag_m = aggregate_metrics(mark_ag)
        ag_m["latency_ms"] = ag_ms
        ag_m["tool_calls"] = tool_calls

        row = {
            "question": question,
            "chatbot": {**cb_m, "ok": score_chatbot(cb_answer), "answer_preview": cb_answer[:200]},
            "agent": {**ag_m, "ok": score_agent(ag_answer, tool_calls), "answer_preview": ag_answer[:200]},
        }
        results.append(row)
        print(f"  chatbot ok={row['chatbot']['ok']} tokens={cb_m['total_tokens']} cost=${cb_m['cost_estimate']:.4f}")
        print(f"  agent   ok={row['agent']['ok']} tokens={ag_m['total_tokens']} tools={tool_calls} cost=${ag_m['cost_estimate']:.4f}")

    n = len(results)
    cb_ok = sum(1 for r in results if r["chatbot"]["ok"])
    ag_ok = sum(1 for r in results if r["agent"]["ok"])

    def avg(key: str, side: str) -> float:
        return sum(r[side][key] for r in results) / n

    summary = {
        "n_cases": n,
        "chatbot_success": cb_ok,
        "agent_success": ag_ok,
        "chatbot_avg_tokens": round(avg("total_tokens", "chatbot")),
        "agent_avg_tokens": round(avg("total_tokens", "agent")),
        "chatbot_avg_latency_ms": round(avg("latency_ms", "chatbot")),
        "agent_avg_latency_ms": round(avg("latency_ms", "agent")),
        "chatbot_avg_cost": round(avg("cost_estimate", "chatbot"), 6),
        "agent_avg_cost": round(avg("cost_estimate", "agent"), 6),
        "agent_avg_tool_calls": round(avg("tool_calls", "agent"), 2),
        "total_cost_compare": round(
            sum(r["chatbot"]["cost_estimate"] + r["agent"]["cost_estimate"] for r in results), 6
        ),
        "agent_latencies": sorted(r["agent"]["latency_ms"] for r in results),
        "results": results,
    }
    lat = summary["agent_latencies"]
    summary["agent_p50_ms"] = lat[len(lat) // 2]
    summary["agent_p99_ms"] = lat[-1]

    out = ROOT / "report" / "evaluation_results.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== SUMMARY ===")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
