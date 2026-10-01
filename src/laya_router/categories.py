"""`laya_router.categories` — the consumer's data: labels with descriptions.

A *label* is a category name; a *category* pairs it with the description Laya
uses to score the option. Categories are **data**, never code: the consumer
supplies them, this library only validates them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Category:
    """One selectable label and the meaning Laya scores it against."""

    label: str
    description: str

    def __post_init__(self) -> None:
        if not self.label or not self.label.strip():
            raise ValueError("a category label must be a non-empty string")
        if not self.description or not self.description.strip():
            raise ValueError(f"category {self.label!r} needs a non-empty description")


def load_labels(path: str | Path) -> list[Category]:
    """Load categories from a YAML file shaped ``labels: {name: description}``.

    Raises ``ValueError`` on a malformed file so a bad dataset never silently
    classifies against the wrong categories (visible failure, no defaults).
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"labels file not found: {source}")
    data: Any = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("labels"), dict):
        raise TypeError(f"{source}: expected a top-level mapping 'labels: {{name: description}}'")

    labels = data["labels"]
    if not labels:
        raise ValueError(f"{source}: 'labels' is empty")

    categories: list[Category] = []
    for label, description in labels.items():
        if not isinstance(label, str) or not isinstance(description, str):
            raise TypeError(f"{source}: every label key and description must be a string")
        categories.append(Category(label=label, description=description))
    return categories


def as_criteria(categories: list[Category]) -> dict[str, str]:
    """The ``choice`` criteria mapping Laya expects: ``{label: description}``."""
    return {category.label: category.description for category in categories}


__all__ = ["Category", "as_criteria", "load_labels"]
