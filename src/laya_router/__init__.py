"""`laya_router` — a generic, domain-free text-to-label router over Laya.

Given a text and a set of labelled categories (data), return the best-fitting
label with a calibrated confidence. Knows nothing about its consumers' domains.
"""

from __future__ import annotations

from .categories import Category, as_criteria, load_labels
from .classifier import Classification, Classifier
from .engine import Engine, LayaEngine
from .metrics import Evaluation, Example, evaluate, load_dataset

__all__ = [
    "Category",
    "Classification",
    "Classifier",
    "Engine",
    "Evaluation",
    "Example",
    "LayaEngine",
    "as_criteria",
    "evaluate",
    "load_dataset",
    "load_labels",
]
