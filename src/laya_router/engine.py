"""`laya_router.engine` — the inference seam.

The classifier talks to an :class:`Engine`, never to Laya directly. Production
uses :class:`LayaEngine`; tests inject a fake, so the fast suite never downloads
a model and stays deterministic.

The engine contract is deliberately small: given a text and the category
criteria, return a probability per label.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Protocol

logger = logging.getLogger(__name__)


class Engine(Protocol):
    """Score category options for a text; return a probability per label."""

    def scores(self, text: str, criteria: Mapping[str, str]) -> dict[str, float]: ...


class LayaEngine:
    """The real engine: Laya's ``choice`` decision, one forward pass.

    Imported lazily so that ``import laya_router`` never pulls the model stack.
    By default it targets the multilingual checkpoint (100+ languages) via the
    single-model SDK; the checkpoint is downloaded once and cached by Laya.
    """

    def __init__(
        self,
        *,
        repo: str = "convaiinnovations/laya",
        subfolder: str = "multilingual",
        device: str = "cpu",
    ) -> None:
        self._repo = repo
        self._subfolder = subfolder
        self._device = device
        self._agent = None

    def _load(self):  # pragma: no cover - needs the real model stack
        if self._agent is None:
            import laya  # lazy: only when a real classification is requested

            logger.info(
                "laya load repo=%s subfolder=%s device=%s",
                self._repo,
                self._subfolder,
                self._device,
            )
            self._agent = laya.load(self._repo, subfolder=self._subfolder)
        return self._agent

    def scores(
        self, text: str, criteria: Mapping[str, str]
    ) -> dict[str, float]:  # pragma: no cover
        agent = self._load()
        questions = {
            "label": {
                "type": "choice",
                "instructions": "Which category fits this text best?",
                "criteria": dict(criteria),
            }
        }
        result = agent.predict(text, questions)
        answer = result["answers"]["label"]["choice"]
        probabilities = result["answers"]["label"].get("probabilities") or {}
        logger.info("laya scored label=%s options=%d", answer, len(criteria))
        if probabilities:
            return {label: float(probabilities.get(label, 0.0)) for label in criteria}
        # Fall back to a one-hot distribution when Laya reports only the choice.
        return {label: 1.0 if label == answer else 0.0 for label in criteria}


__all__ = ["Engine", "LayaEngine"]
