# Lab 3: Chatbot vs ReAct Agent (Industry Edition)

Welcome to Phase 3 of the Agentic AI course! This lab focuses on moving from a simple LLM Chatbot to a sophisticated **ReAct Agent** with industry-standard monitoring.

## 🚀 Getting Started

### 1. Setup Environment
Copy the `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. LLM providers (switch in `.env`)

| `DEFAULT_PROVIDER` | Key | Model example |
|--------------------|-----|----------------|
| `mimo` | `MIMO_API_KEY` | `mimo-v2.5-pro` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| `google` | `GEMINI_API_KEY` | `gemini-2.5-flash` |

```bash
python scripts/test_provider.py mimo
python scripts/test_provider.py google   # rubric: demo provider switch
```

MiMo uses an OpenAI-compatible client (`base_url=https://api.xiaomimimo.com/v1`). Chatbot and agent use the same `get_llm_from_env()` — only the LLM backend changes.

### 4. Directory Structure
- `src/tools/`: Resort review tools (mock multi-platform data).
- `data/reviews_sunrise_bay.json`: Mock reviews for **Sunrise Bay Resort** only.

## 🏨 Resort domain (team project)

**Problem:** Guest reviews on TripAdvisor, Booking, Google, Agoda, social — recurring issues (noisy rooms, weak breakfast, slow check-in) are missed until ratings drop.

**Lab scope (mock data, one resort, no crawling):** ReAct agent calls tools to search reviews, summarize sentiment by aspect, and list top issues with quotes.

```bash
python scripts/test_provider.py
python -m pytest tests/test_resort_tools.py -q
python scripts/run_chatbot.py "Khách phàn nàn gì về phòng và ăn sáng?"
python scripts/run_agent.py
```

### Web UI — so sánh Chatbot vs ReAct

**HTML (khuyên dùng):**

```bash
pip install flask
python app/server.py
```

Mở trình duyệt:

| URL | Mục đích |
|-----|----------|
| **http://127.0.0.1:5000/** | Demo chat (so sánh Chatbot vs ReAct) |
| **http://127.0.0.1:5000/present/** | **Web thuyết trình** (10 slide, phím ← →) |

**Lỗi 404?** Phải chạy `python app/server.py` (không mở file HTML trực tiếp, không dùng Streamlit cho slide). Sau khi sửa code, **tắt server cũ (Ctrl+C) và chạy lại**.

**Streamlit (tuỳ chọn):**

```bash
streamlit run app/demo.py
```

Test cases: `tests/test_cases_resort.txt`. Logs: `logs/`.

| Tool | Purpose |
|------|---------|
| `search_reviews` | Filter by aspect / keyword |
| `sentiment_summary` | Positive / negative / neutral counts |
| `top_issues` | Recurring complaints + quotes |

## 🏠 Running with Local Models (CPU)

If you don't want to use OpenAI or Gemini, you can run open-source models (like Phi-3) directly on your CPU using `llama-cpp-python`.

### 1. Download the Model
Download the **Phi-3-mini-4k-instruct-q4.gguf** (approx 2.2GB) from Hugging Face:
- [Phi-3-mini-4k-instruct-GGUF](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
- Direct Download: [phi-3-mini-4k-instruct-q4.gguf](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf)

### 2. Place Model in Project
Create a `models/` folder in the root and move the downloaded `.gguf` file there.

### 3. Update `.env`
Change your `DEFAULT_PROVIDER` and set the path:
```env
DEFAULT_PROVIDER=local
LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
```

## 🎯 Lab Objectives

1.  **Baseline Chatbot**: Observe the limitations of a standard LLM when faced with multi-step reasoning.
2.  **ReAct Loop**: Implement the `Thought-Action-Observation` cycle in `src/agent/agent.py`.
3.  **Provider Switching**: Swap between OpenAI and Gemini seamlessly using the `LLMProvider` interface.
4.  **Failure Analysis**: Use the structured logs in `logs/` to identify why the agent fails (hallucinations, parsing errors).
5.  **Grading & Bonus**: Follow the [SCORING.md](file:///Users/tindt/personal/ai-thuc-chien/day03-lab-agent/SCORING.md) to maximize your points and explore bonus metrics.

## 🛠️ How to Use This Baseline
The code is designed as a **Production Prototype**. It includes:
- **Telemetry**: Every action is logged in JSON format for later analysis.
- **Robust Provider Pattern**: Easily extendable to any LLM API.
- **Clean Skeletons**: Focus on the logic that matters—the agent's reasoning process.

---

*Happy Coding! Let's build agents that actually work.*
