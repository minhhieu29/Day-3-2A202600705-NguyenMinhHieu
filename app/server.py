"""
HTML demo server: Chatbot vs ReAct comparison.

Run: python app/server.py
Open: http://127.0.0.1:5000
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from src.agent.agent import ReActAgent
from src.chatbot import ResortChatbot
from src.core.provider_factory import get_llm_from_env
from src.tools import TOOLS
from src.telemetry.metrics import tracker

STATIC_DIR = Path(__file__).parent / "static"
PRESENTATION_DIR = Path(__file__).parent / "presentation"

# static_url_path must NOT be "" — that registers /<path:filename> at root
# and can return 404 for /present/styles.css before our presentation routes run.
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")


def _format_trace(history: list[str]) -> str:
    return "\n\n".join(b for b in history if not b.startswith("User question:"))


def _aggregate_llm_metrics(start_index: int) -> dict:
    """Sum LLM_METRIC rows recorded since start_index (one row per llm.generate)."""
    chunk = tracker.session_metrics[start_index:]
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


def _usage_payload(start_index: int, wall_ms: int, **extra) -> dict:
    payload = _aggregate_llm_metrics(start_index)
    payload["latency_ms"] = wall_ms
    payload.update(extra)
    return payload


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/style.css")
def legacy_style_css():
    return send_from_directory(STATIC_DIR, "style.css")


@app.get("/app.js")
def legacy_app_js():
    return send_from_directory(STATIC_DIR, "app.js")


@app.get("/presentation")
def presentation_alias():
    return redirect("/present/", code=302)


@app.get("/present")
def presentation_redirect():
    return redirect("/present/", code=302)


@app.get("/present/")
def presentation_index():
    if not PRESENTATION_DIR.is_dir():
        return jsonify({"ok": False, "error": "Thiếu thư mục app/presentation"}), 500
    return send_from_directory(PRESENTATION_DIR, "index.html")


@app.get("/present/<path:filename>")
def presentation_static(filename: str):
    if not PRESENTATION_DIR.is_dir():
        return jsonify({"ok": False, "error": "Thiếu thư mục app/presentation"}), 500
    return send_from_directory(PRESENTATION_DIR, filename)


@app.get("/api/config")
def config():
    try:
        llm = get_llm_from_env()
        return jsonify({
            "ok": True,
            "provider": os.getenv("DEFAULT_PROVIDER", "?"),
            "model": llm.model_name,
            "tools": [t["name"] for t in TOOLS],
        })
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/chatbot")
def api_chatbot():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Thiếu câu hỏi"}), 400
    try:
        llm = get_llm_from_env()
        mark = len(tracker.session_metrics)
        t0 = time.time()
        answer = ResortChatbot(llm).run(question)
        ms = int((time.time() - t0) * 1000)
        return jsonify({
            "ok": True,
            "answer": answer,
            "mode": "chatbot",
            **_usage_payload(mark, ms),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/agent")
def api_agent():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()
    max_steps = int(data.get("max_steps") or 6)
    if not question:
        return jsonify({"ok": False, "error": "Thiếu câu hỏi"}), 400
    try:
        llm = get_llm_from_env()
        mark = len(tracker.session_metrics)
        t0 = time.time()
        agent = ReActAgent(llm=llm, tools=TOOLS, max_steps=max_steps)
        answer = agent.run(question)
        ms = int((time.time() - t0) * 1000)
        tool_calls = sum(1 for h in agent.history if h.startswith("Action:"))
        return jsonify({
            "ok": True,
            "answer": answer,
            "trace": _format_trace(agent.history),
            "tool_calls": tool_calls,
            "mode": "react",
            **_usage_payload(mark, ms),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/compare")
def api_compare():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()
    max_steps = int(data.get("max_steps") or 6)
    if not question:
        return jsonify({"ok": False, "error": "Thiếu câu hỏi"}), 400

    try:
        llm = get_llm_from_env()

        mark_cb = len(tracker.session_metrics)
        t0 = time.time()
        chatbot_answer = ResortChatbot(llm).run(question)
        chatbot_ms = int((time.time() - t0) * 1000)
        chatbot_usage = _usage_payload(mark_cb, chatbot_ms)

        mark_ag = len(tracker.session_metrics)
        t0 = time.time()
        agent = ReActAgent(llm=llm, tools=TOOLS, max_steps=max_steps)
        agent_answer = agent.run(question)
        agent_ms = int((time.time() - t0) * 1000)
        tool_calls = sum(1 for h in agent.history if h.startswith("Action:"))
        agent_usage = _usage_payload(mark_ag, agent_ms, tool_calls=tool_calls)

        return jsonify({
            "ok": True,
            "question": question,
            "chatbot": {"answer": chatbot_answer, **chatbot_usage},
            "agent": {
                "answer": agent_answer,
                "trace": _format_trace(agent.history),
                **agent_usage,
            },
            "comparison": {
                "token_delta": agent_usage["total_tokens"] - chatbot_usage["total_tokens"],
                "cost_delta": round(
                    agent_usage["cost_estimate"] - chatbot_usage["cost_estimate"], 6
                ),
            },
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("Sunrise Bay demo server (restart sau khi pull/sua code)")
    print("Demo chat:    http://127.0.0.1:5000/")
    print("Thuyet trinh: http://127.0.0.1:5000/present/")
    print("=" * 50)
    if not PRESENTATION_DIR.is_dir():
        print("CANH BAO: thieu app/presentation/ — slide se loi.")
    app.run(host="127.0.0.1", port=5000, debug=False)
