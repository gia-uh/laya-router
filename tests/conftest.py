"""Shared test fixtures: a deterministic fake engine (no model download)."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from laya_router.categories import Category


class FakeEngine:
    """A scripted engine: return the stored scores for the given text.

    Keeps the fast suite deterministic and model-free; the real Laya path is a
    separate, opted-in integration test.
    """

    def __init__(self, table: Mapping[str, Mapping[str, float]]) -> None:
        self._table = {text: dict(scores) for text, scores in table.items()}
        self.calls: list[tuple[str, dict[str, str]]] = []

    def scores(self, text: str, criteria: Mapping[str, str]) -> dict[str, float]:
        self.calls.append((text, dict(criteria)))
        if text in self._table:
            return dict(self._table[text])
        # Default: the first option dominates deterministically.
        labels = list(criteria)
        return {label: (1.0 if index == 0 else 0.0) for index, label in enumerate(labels)}


@pytest.fixture
def categories() -> list[Category]:
    return [
        Category("to_do", "a list of tasks to do"),
        Category("reminder", "events with dates or times"),
        Category("idea", "an idea or reflection to capture"),
    ]
