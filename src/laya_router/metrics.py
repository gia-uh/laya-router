"""`laya_router.metrics` — turn "it looks right" into a number.

Given a labelled dataset and a classifier, compute accuracy, the confusion
matrix, and a threshold↔coverage curve. Domain-free: a row is ``text`` plus the
expected ``label``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .classifier import Classifier


@dataclass(frozen=True)
class Example:
    """One labelled evaluation row."""

    text: str
    label: str


@dataclass
class Evaluation:
    """The outcome over a dataset: accuracy, confusion, threshold curve."""

    total: int
    correct: int
    accuracy: float
    labels: list[str]
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    threshold_curve: list[tuple[float, float, float]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "correct": self.correct,
            "accuracy": self.accuracy,
            "confusion": self.confusion,
            "threshold_curve": [
                {"threshold": t, "coverage": c, "accuracy": a} for t, c, a in self.threshold_curve
            ],
        }


def load_dataset(path: str | Path) -> list[Example]:
    """Load a JSONL dataset: one ``{"text": ..., "label": ...}`` per line."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"dataset not found: {source}")
    examples: list[Example] = []
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source}:{number}: not valid JSON") from exc
        text, label = row.get("text"), row.get("label")
        if not isinstance(text, str) or not isinstance(label, str):
            raise TypeError(f"{source}:{number}: needs string 'text' and 'label'")
        examples.append(Example(text=text, label=label))
    if not examples:
        raise ValueError(f"{source}: no examples")
    return examples


def evaluate(
    classifier: Classifier,
    examples: list[Example],
    *,
    thresholds: tuple[float, ...] = (0.0, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
) -> Evaluation:
    """Run ``classifier`` over ``examples`` and summarise the outcome."""
    labels = sorted({category.label for category in classifier._categories})
    confusion: dict[str, dict[str, int]] = {
        expected: dict.fromkeys(labels, 0) for expected in labels
    }

    predictions: list[tuple[Example, str, float]] = []
    correct = 0
    for example in examples:
        result = classifier.classify(example.text)
        predictions.append((example, result.label, result.confidence))
        confusion.setdefault(example.label, dict.fromkeys(labels, 0))
        confusion.setdefault(result.label, dict.fromkeys(labels, 0))
        confusion[example.label][result.label] += 1
        if result.label == example.label:
            correct += 1

    total = len(examples)
    curve: list[tuple[float, float, float]] = []
    for threshold in thresholds:
        covered = [(ex, label) for ex, label, conf in predictions if conf >= threshold]
        coverage = len(covered) / total if total else 0.0
        accuracy = (
            sum(1 for ex, label in covered if label == ex.label) / len(covered) if covered else 0.0
        )
        curve.append((threshold, coverage, accuracy))

    return Evaluation(
        total=total,
        correct=correct,
        accuracy=correct / total if total else 0.0,
        labels=labels,
        confusion=confusion,
        threshold_curve=curve,
    )


__all__ = ["Evaluation", "Example", "evaluate", "load_dataset"]
