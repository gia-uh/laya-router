"""`laya_router.classifier` — text to the best-fitting label.

The classifier is the library's public surface. It is **informative, not
prescriptive**: it always returns the best label and its calibrated confidence,
plus a ``below_threshold`` flag; the consumer decides what to do with a weak
answer (ask again, show a menu, fall back).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .categories import Category, as_criteria
from .engine import Engine, LayaEngine

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Classification:
    """The result: the best label, its confidence, the ranking, the flag."""

    label: str
    confidence: float
    below_threshold: bool
    scores: dict[str, float]

    def ranked(self, top_k: int | None = None) -> list[tuple[str, float]]:
        """Labels sorted by descending probability (optionally the first ``top_k``)."""
        ordered = sorted(self.scores.items(), key=lambda item: item[1], reverse=True)
        return ordered if top_k is None else ordered[:top_k]


class Classifier:
    """Route a text to one of the configured categories.

    ``engine`` is injectable so tests need no model; the default builds the real
    Laya engine lazily.
    """

    def __init__(
        self,
        categories: list[Category],
        *,
        threshold: float = 0.0,
        engine: Engine | None = None,
    ) -> None:
        if not categories:
            raise ValueError("at least one category is required")
        labels = [category.label for category in categories]
        if len(set(labels)) != len(labels):
            raise ValueError("category labels must be unique")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be within [0, 1]")

        self._categories = list(categories)
        self._criteria = as_criteria(self._categories)
        self._threshold = threshold
        self._engine: Engine = engine if engine is not None else LayaEngine()

    @property
    def threshold(self) -> float:
        return self._threshold

    def classify(self, text: str) -> Classification:
        """Return the best-fitting label for ``text`` with calibrated confidence."""
        if not text or not text.strip():
            raise ValueError("cannot classify an empty text")

        scores = self._engine.scores(text, self._criteria)
        unknown = set(scores) - set(self._criteria)
        if unknown:
            raise ValueError(f"engine returned unknown labels: {sorted(unknown)}")
        if not scores:
            raise ValueError("engine returned no scores")

        label, confidence = max(scores.items(), key=lambda item: item[1])
        below = confidence < self._threshold
        logger.info(
            "classified label=%s confidence=%.3f below_threshold=%s categories=%d",
            label,
            confidence,
            below,
            len(self._categories),
        )
        return Classification(
            label=label,
            confidence=confidence,
            below_threshold=below,
            scores=dict(scores),
        )


__all__ = ["Classification", "Classifier"]
