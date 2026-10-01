"""The CLI: classify prints JSON; evaluate delegates to the classifier.

The CLI builds a real ``Classifier`` (Laya engine), which would download a model.
To keep the fast suite offline, these tests monkeypatch the classifier factory.
"""

from __future__ import annotations

import json
import pathlib

from laya_router import cli
from laya_router.categories import Category
from laya_router.classifier import Classifier
from tests.conftest import FakeEngine

CATEGORIES = [
    Category("to_do", "a list of tasks"),
    Category("reminder", "events with dates or times"),
]


def _labels_file(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "labels.yaml"
    path.write_text("labels:\n  to_do: a list of tasks\n  reminder: events with dates\n")
    return path


def _patch_engine(monkeypatch, table: dict[str, dict[str, float]]) -> None:
    """Replace the default engine so no model is built."""
    original = Classifier.__init__

    def patched(self, categories, *, threshold=0.0, engine=None):  # type: ignore[no-untyped-def]
        original(self, categories, threshold=threshold, engine=FakeEngine(table))

    monkeypatch.setattr(Classifier, "__init__", patched)


def test_cli_classify(monkeypatch, tmp_path: pathlib.Path, capsys) -> None:
    _patch_engine(monkeypatch, {"buy milk": {"to_do": 0.9, "reminder": 0.1}})
    code = cli.main(["classify", "--labels", str(_labels_file(tmp_path)), "--text", "buy milk"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["label"] == "to_do"
    assert out["confidence"] == 0.9
    assert out["below_threshold"] is False


def test_cli_evaluate(monkeypatch, tmp_path: pathlib.Path, capsys) -> None:
    _patch_engine(monkeypatch, {"buy milk": {"to_do": 0.9, "reminder": 0.1}})
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text('{"text": "buy milk", "label": "to_do"}\n')
    code = cli.main(
        ["evaluate", "--labels", str(_labels_file(tmp_path)), "--dataset", str(dataset)]
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["accuracy"] == 1.0
    assert out["total"] == 1
