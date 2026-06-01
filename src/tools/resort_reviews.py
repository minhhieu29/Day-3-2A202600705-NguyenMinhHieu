"""
Resort guest-review tools (mock multi-platform data for Lab 3).

Domain: Sunrise Bay Resort only — TripAdvisor, Booking, Google, Agoda, social.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REVIEWS_PATH = DATA_DIR / "reviews_sunrise_bay.json"
RESORT_NAME = "Sunrise Bay Resort"

NEGATIVE_WORDS = {
    "noisy", "noise", "loud", "slow", "cheap", "poor", "bad", "terrible", "disappointing",
    "weak", "limited", "rattled", "thin", "nghèo", "chậm", "ồn", "khó", "khô", "lâu",
}
POSITIVE_WORDS = {
    "excellent", "beautiful", "friendly", "well", "good", "great", "love", "peaceful",
    "quick", "modern", "nhiệt tình", "phong phú", "đẹp",
}

ASPECT_ALIASES = {
    "room": "room",
    "rooms": "room",
    "phòng": "room",
    "breakfast": "breakfast",
    "food": "breakfast",
    "ăn sáng": "breakfast",
    "dining": "breakfast",
    "checkin": "checkin",
    "check-in": "checkin",
    "check in": "checkin",
    "reception": "checkin",
    "lễ tân": "checkin",
    "service": "service",
    "staff": "service",
    "amenities": "amenities",
    "pool": "amenities",
    "spa": "amenities",
    "value": "value",
    "price": "value",
    "giá": "value",
}


def _normalize_aspect(aspect: str) -> str:
    key = aspect.strip().lower()
    return ASPECT_ALIASES.get(key, key)


def _load_reviews() -> List[Dict[str, Any]]:
    if not REVIEWS_PATH.exists():
        raise FileNotFoundError(f"Review data not found: {REVIEWS_PATH}")
    with open(REVIEWS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _sentiment_label(text: str, rating: int) -> str:
    lower = text.lower()
    neg = sum(1 for w in NEGATIVE_WORDS if w in lower)
    pos = sum(1 for w in POSITIVE_WORDS if w in lower)
    if rating <= 2 or neg > pos + 1:
        return "negative"
    if rating >= 4 and pos >= neg:
        return "positive"
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def search_reviews(aspect: str, keyword: Optional[str] = None) -> str:
    """Search reviews by aspect (room, breakfast, checkin, service, amenities, value). Optional keyword e.g. 'noise'."""
    reviews = _load_reviews()
    aspect_norm = _normalize_aspect(aspect)
    matched = [r for r in reviews if r.get("aspect") == aspect_norm]
    if keyword:
        kw = keyword.lower()
        matched = [r for r in matched if kw in r["text"].lower()]
    payload = {
        "resort": RESORT_NAME,
        "aspect": aspect_norm,
        "keyword": keyword,
        "count": len(matched),
        "reviews": matched[:8],
    }
    return json.dumps(payload, ensure_ascii=False)


def sentiment_summary(aspect: str) -> str:
    """Sentiment counts (positive/negative/neutral) and average rating for one aspect."""
    reviews = _load_reviews()
    aspect_norm = _normalize_aspect(aspect)
    subset = [r for r in reviews if r.get("aspect") == aspect_norm]
    counts: Counter[str] = Counter()
    for r in subset:
        counts[_sentiment_label(r["text"], r["rating"])] += 1
    avg_rating = round(sum(r["rating"] for r in subset) / len(subset), 2) if subset else 0
    payload = {
        "resort": RESORT_NAME,
        "aspect": aspect_norm,
        "total_reviews": len(subset),
        "average_rating": avg_rating,
        "sentiment": dict(counts),
    }
    return json.dumps(payload, ensure_ascii=False)


def top_issues(limit: int = 5) -> str:
    """Top recurring complaint themes with example quotes from negative reviews."""
    reviews = _load_reviews()
    negative = [r for r in reviews if _sentiment_label(r["text"], r["rating"]) == "negative"]
    by_aspect: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in negative:
        by_aspect[r["aspect"]].append(r)

    issues = []
    for aspect, items in sorted(by_aspect.items(), key=lambda x: -len(x[1])):
        issues.append({
            "aspect": aspect,
            "complaint_count": len(items),
            "platforms": sorted({i["platform"] for i in items}),
            "example_quotes": [i["text"] for i in items[:2]],
        })
        if len(issues) >= int(limit):
            break

    payload = {
        "resort": RESORT_NAME,
        "negative_review_count": len(negative),
        "top_issues": issues,
    }
    return json.dumps(payload, ensure_ascii=False)


TOOLS = [
    {
        "name": "search_reviews",
        "description": (
            "Search guest reviews by aspect. "
            "aspect: room, breakfast, checkin, service, amenities, value. "
            "Optional keyword (string) e.g. 'noise'. "
            "Example: search_reviews('room', 'noise')"
        ),
        "func": search_reviews,
    },
    {
        "name": "sentiment_summary",
        "description": (
            "Sentiment breakdown for one aspect (positive/negative/neutral, avg rating). "
            "Example: sentiment_summary('breakfast')"
        ),
        "func": sentiment_summary,
    },
    {
        "name": "top_issues",
        "description": (
            "Top recurring complaints with quotes. limit: int, default 5. Example: top_issues(3)"
        ),
        "func": top_issues,
    },
]
