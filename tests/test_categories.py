"""Categories are the consumer's data: loading and validation."""

from __future__ import annotations

import pathlib

import pytest

from laya_router.categories import Category, as_criteria, load_labels


def test_category_rejects_missing_description() -> None:
    with pytest.raises(ValueError):
        Category("to_do", "   ")


def test_load_labels_from_yaml(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "labels.yaml"
    path.write_text(
        "labels:\n  to_do: a list of tasks\n  idea: an idea to capture\n", encoding="utf-8"
    )
    categories = load_labels(path)
    assert [category.label for category in categories] == ["to_do", "idea"]
    assert as_criteria(categories)["idea"] == "an idea to capture"


def test_load_labels_rejects_malformed(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "labels.yaml"
    path.write_text("categories:\n  - to_do\n", encoding="utf-8")
    with pytest.raises(TypeError):
        load_labels(path)


def test_load_labels_rejects_empty(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "labels.yaml"
    path.write_text("labels: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_labels(path)


def test_load_labels_missing_file(tmp_path: pathlib.Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_labels(tmp_path / "nope.yaml")
