"""
Lab 3 demo UI: compare Chatbot vs ReAct Agent side by side.

Run: streamlit run app/demo.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from src.agent.agent import ReActAgent
from src.chatbot import ResortChatbot
from src.core.provider_factory import get_llm_from_env
from src.tools import TOOLS

PRESET_QUESTIONS = [
    "Khách phàn nàn gì về phòng và ăn sáng tại Sunrise Bay? Đưa trích dẫn. Đề xuất 2 ưu tiên cải thiện.",
    "Top 3 vấn đề lặp lại từ review tiêu cực là gì?",
    "Ăn sáng được đánh giá thế nào? Tóm tắt sentiment khía cạnh breakfast.",
    "Check-in chậm có phải vấn đề lặp lại không? Tìm review liên quan.",
]

st.set_page_config(
    page_title="Sunrise Bay — Chatbot vs ReAct",
    page_icon="🏨",
    layout="wide",
)


@st.cache_resource
def load_llm():
    return get_llm_from_env()


def format_react_trace(history: list[str]) -> str:
    lines = []
    for block in history:
        if block.startswith("User question:"):
            continue
        lines.append(block)
    return "\n\n".join(lines) if lines else "(chưa có trace)"


def main() -> None:
    st.title("🏨 Sunrise Bay Resort — Chatbot vs ReAct Agent")
    st.caption(
        "So sánh trực quan: Chatbot (1 lần LLM, không tool) · ReAct (Thought → Action → Observation → Final Answer)"
    )

    try:
        llm = load_llm()
    except ValueError as exc:
        st.error(f"Cấu hình .env: {exc}")
        st.stop()

    col_cfg, col_info = st.columns([2, 1])
    with col_cfg:
        provider = os.getenv("DEFAULT_PROVIDER", "?")
        model = os.getenv("DEFAULT_MODEL", llm.model_name)
        max_steps = st.slider("Agent max steps", 3, 10, 6)
    with col_info:
        st.info(f"**Provider:** `{provider}`\n\n**Model:** `{model}`\n\n**Tools:** {len(TOOLS)}")

    if "question_input" not in st.session_state:
        st.session_state.question_input = PRESET_QUESTIONS[0]

    st.write("**Câu mẫu:**")
    preset_cols = st.columns(len(PRESET_QUESTIONS))
    for i, preset in enumerate(PRESET_QUESTIONS):
        if preset_cols[i].button(f"Mẫu {i + 1}", key=f"preset_{i}"):
            st.session_state.question_input = preset

    question = st.text_area(
        "Câu hỏi",
        height=100,
        placeholder="Nhập câu hỏi về review khách...",
        key="question_input",
    )

    run_chatbot = st.button("▶ Chỉ Chatbot", use_container_width=False)
    run_agent = st.button("▶ Chỉ ReAct Agent", use_container_width=False)
    run_both = st.button("⚡ So sánh cả hai", type="primary", use_container_width=False)

    if not (run_chatbot or run_agent or run_both):
        st.divider()
        st.markdown(
            """
            | | **Chatbot** | **ReAct Agent** |
            |--|-------------|-----------------|
            | API calls | Thường **1** | **2+** (mỗi bước suy nghĩ) |
            | Tools | ❌ | ✅ `search_reviews`, `sentiment_summary`, `top_issues` |
            | Dữ liệu review | Đoán / kiến thức chung | Đọc `data/reviews_sunrise_bay.json` |
            | Phù hợp | Câu đơn giản | Câu nhiều bước + trích dẫn |
            """
        )
        return

    left, right = st.columns(2)

    chatbot_answer = None
    chatbot_ms = None
    agent_answer = None
    agent_trace = None
    agent_ms = None
    agent_steps = None

    if run_chatbot or run_both:
        with left:
            with st.spinner("Chatbot đang trả lời..."):
                t0 = time.time()
                try:
                    chatbot_answer = ResortChatbot(llm).run(question)
                    chatbot_ms = int((time.time() - t0) * 1000)
                except Exception as exc:
                    chatbot_answer = f"**Lỗi:** {exc}"

    if run_agent or run_both:
        with right:
            with st.spinner("ReAct Agent đang suy luận + gọi tool..."):
                t0 = time.time()
                try:
                    agent = ReActAgent(llm=llm, tools=TOOLS, max_steps=max_steps)
                    agent_answer = agent.run(question)
                    agent_trace = format_react_trace(agent.history)
                    agent_ms = int((time.time() - t0) * 1000)
                    agent_steps = sum(
                        1 for h in agent.history if h.startswith("Action:")
                    )
                except Exception as exc:
                    agent_answer = f"**Lỗi:** {exc}"

    st.divider()

    with left:
        st.subheader("💬 Chatbot (baseline)")
        st.caption("Không dùng tool · một lần gọi LLM")
        if chatbot_ms is not None:
            st.metric("Thời gian", f"{chatbot_ms} ms")
        if chatbot_answer:
            st.markdown(chatbot_answer)
        elif run_agent and not run_both:
            st.info("Bấm **So sánh cả hai** hoặc **Chỉ Chatbot** để chạy.")

    with right:
        st.subheader("🔄 ReAct Agent")
        st.caption("Thought → Action → Observation → Final Answer")
        if agent_ms is not None:
            c1, c2 = st.columns(2)
            c1.metric("Thời gian", f"{agent_ms} ms")
            c2.metric("Tool calls", agent_steps or 0)
        if agent_answer:
            st.markdown(agent_answer)
            if agent_trace:
                with st.expander("📜 ReAct trace (Thought / Action / Observation)", expanded=True):
                    st.code(agent_trace, language=None)
        elif run_chatbot and not run_both:
            st.info("Bấm **So sánh cả hai** hoặc **Chỉ ReAct Agent** để chạy.")

    if chatbot_answer and agent_answer and (run_both or (run_chatbot and run_agent)):
        st.divider()
        st.subheader("📊 Gợi ý so sánh nhanh")
        st.markdown(
            "- **Chatbot** thường trả lời chung, ít/không có trích dẫn từ file review.\n"
            "- **ReAct** nên có `Action:` trong trace và trích dẫn khách trong Final Answer.\n"
            "- Log chi tiết: thư mục `logs/` (JSON telemetry)."
        )


if __name__ == "__main__":
    main()
