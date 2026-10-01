"""Evaluation: accuracy, confusion matrix and threshold curve."""

from __future__ import annotations

import pathlib

import pytest

from laya_router.categories import Category
from laya_router.classifier import Classifier
from laya_router.metrics import Example, evaluate, load_dataset
from tests.conftest import FakeEngine

CATEGORIES = [
    Category("to_do", "a list of tasks"),
    Category("reminder", "events with dates or times"),
]


def test_evaluate_computes_accuracy_and_confusion() -> None:
    engine = FakeEngine(
        {
            "buy milk": {"to_do": 0.9, "reminder": 0.1},  # right
            "call ana": {"to_do": 0.7, "reminder": 0.3},  # wrong (expected reminder)
        }
    )
    classifier = Classifier(CATEGORIES, engine=engine)
    examples = [Example("buy milk", "to_do"), Example("call ana", "reminder")]
    result = evaluate(classifier, examples)
    assert result.total == 2
    assert result.correct == 1
    assert result.accuracy == pytest.approx(0.5)
    assert result.confusion["reminder"]["to_do"] == 1
    assert result.confusion["to_do"]["to_do"] == 1


def test_threshold_curve_trades_coverage_for_accuracy() -> None:
    engine = FakeEngine(
        {
            "sure right": {"to_do": 0.95, "reminder": 0.05},
            "unsure wrong": {"to_do": 0.55, "reminder": 0.45},
        }
    )
    classifier = Classifier(CATEGORIES, engine=engine)
    examples = [Example("sure right", "to_do"), Example("unsure wrong", "reminder")]
    result = evaluate(classifier, examples, thresholds=(0.0, 0.6, 0.9))
    by_threshold = {t: (c, a) for t, c, a in result.threshold_curve}
    assert by_threshold[0.0] == (1.0, 0.5)  # everything, half right
    assert by_threshold[0.6] == (0.5, 1.0)  # only the sure one, all right
    assert by_threshold[0.9] == (0.5, 1.0)


def test_load_dataset_jsonl(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "eval.jsonl"
    path.write_text('{"text": "a", "label": "to_do"}\n\n{"text": "b", "label": "reminder"}\n')
    examples = load_dataset(path)
    assert [example.label for example in examples] == ["to_do", "reminder"]


def test_load_dataset_rejects_bad_row(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "eval.jsonl"
    path.write_text('{"text": "a"}\n', encoding="utf-8")
    with pytest.raises(TypeError):
        load_dataset(path)


def test_load_dataset_rejects_empty(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "eval.jsonl"
    path.write_text("\n\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_dataset(path)
