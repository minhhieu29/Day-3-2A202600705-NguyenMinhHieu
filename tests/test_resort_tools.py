import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.tools.resort_reviews import search_reviews, sentiment_summary, top_issues


def test_search_reviews_room():
    out = search_reviews("room")
    assert "noisy" in out.lower() or "noise" in out.lower()


def test_sentiment_breakfast_negative():
    out = sentiment_summary("breakfast")
    assert "negative" in out


def test_top_issues():
    out = top_issues(3)
    assert "top_issues" in out
