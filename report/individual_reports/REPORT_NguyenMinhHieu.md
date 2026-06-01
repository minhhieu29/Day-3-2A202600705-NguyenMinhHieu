# Individual Report: Lab 3 — Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Minh Hiếu
- **Student ID**: 2A202600705
- **Role**: Tools & Data
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Thiết kế **domain resort** (Sunrise Bay): mock data và **3 tool** cho ReAct agent.

| Module | Mô tả |
| :--- | :--- |
| `data/reviews_sunrise_bay.json` | 20 review (aspect, rating, platform, EN/VI) |
| `src/tools/resort_reviews.py` | `search_reviews`, `sentiment_summary`, `top_issues` |
| `src/tools/__init__.py` | Export `TOOLS` cho agent |
| `tests/test_resort_tools.py` | Unit test tool |

**`search_reviews`** — lọc theo aspect (alias tiếng Việt) và keyword:

```python
def search_reviews(aspect: str, keyword: Optional[str] = None) -> str:
```

**`ASPECT_ALIASES`** — map `phòng` → `room`, `ăn sáng` → `breakfast`.

Agent gọi tool → **Observation** (text) → LLM tiếp tục hoặc Final Answer. Mô tả trong `TOOLS[].description` là hợp đồng LLM đọc khi chọn Action.

---

## II. Debugging Case Study (10 Points)

**Problem:** `search_reviews("phòng")` trả *No reviews found* dù data có `aspect: "room"`.

**Diagnosis:** Tham số tiếng Việt / biến thể (`check-in`) không khớp key JSON.

**Solution:** `_normalize_aspect()` + `ASPECT_ALIASES` trong `resort_reviews.py`.

**Kết quả:** `pytest tests/test_resort_tools.py` pass.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning:** Chatbot không có Thought/Action — không chứng minh claim bằng observation; tool buộc agent trích quote từ JSON.
2. **Reliability:** Agent có thể over-tooling; chatbot nhanh hơn nhưng dễ hallucination.
3. **Observation:** Sau `sentiment_summary`, agent biết breakfast negative và có thể `search_reviews` lấy quote.

---

## IV. Future Improvements (5 Points)

- DB/warehouse thay file JSON; pagination `search_reviews`.
- Giới hạn độ dài Observation; redact PII.
- Index aspect + embedding khi dataset lớn.
