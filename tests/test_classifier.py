"""The classifier: best label, calibrated confidence, threshold flag."""

from __future__ import annotations

import pytest

from laya_router.categories import Category
from laya_router.classifier import Classifier
from tests.conftest import FakeEngine

CATEGORIES = [
    Category("to_do", "a list of tasks"),
    Category("reminder", "events with dates or times"),
]


def test_classify_picks_the_best_label() -> None:
    engine = FakeEngine({"buy milk": {"to_do": 0.9, "reminder": 0.1}})
    result = Classifier(CATEGORIES, engine=engine).classify("buy milk")
    assert result.label == "to_do"
    assert result.confidence == pytest.approx(0.9)
    assert result.below_threshold is False


def test_threshold_marks_low_confidence() -> None:
    engine = FakeEngine({"maybe": {"to_do": 0.55, "reminder": 0.45}})
    result = Classifier(CATEGORIES, threshold=0.6, engine=engine).classify("maybe")
    assert result.label == "to_do"  # still the best, just flagged
    assert result.below_threshold is True


def test_ranked_returns_descending_order() -> None:
    engine = FakeEngine({"x": {"to_do": 0.2, "reminder": 0.8}})
    result = Classifier(CATEGORIES, engine=engine).classify("x")
    assert result.ranked() == [("reminder", 0.8), ("to_do", 0.2)]
    assert result.ranked(top_k=1) == [("reminder", 0.8)]


def test_engine_receives_the_criteria_as_data() -> None:
    engine = FakeEngine({})
    Classifier(CATEGORIES, engine=engine).classify("anything")
    _, criteria = engine.calls[0]
    assert criteria == {"to_do": "a list of tasks", "reminder": "events with dates or times"}


def test_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        Classifier(CATEGORIES, engine=FakeEngine({})).classify("   ")


def test_rejects_duplicate_labels() -> None:
    with pytest.raises(ValueError):
        Classifier([Category("a", "x"), Category("a", "y")], engine=FakeEngine({}))


def test_rejects_no_categories() -> None:
    with pytest.raises(ValueError):
        Classifier([], engine=FakeEngine({}))


def test_rejects_engine_returning_unknown_labels() -> None:
    engine = FakeEngine({"x": {"ghost": 1.0}})
    with pytest.raises(ValueError):
        Classifier(CATEGORIES, engine=engine).classify("x")
