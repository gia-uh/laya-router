"""Real-Laya integration test (opt-in; downloads the checkpoint, runs on CPU).

Run with `make test-integration`. Kept out of the fast gate because it pulls a
~650 MB checkpoint and is slow on CPU. It proves the seam end to end: a real
``Classifier`` with the default ``LayaEngine`` maps texts to sane labels.
"""

from __future__ import annotations

import pytest

from laya_router.categories import Category
from laya_router.classifier import Classifier

pytestmark = pytest.mark.integration


def test_real_laya_routes_obvious_texts() -> None:
    classifier = Classifier(
        [
            Category("to_do", "a list of tasks to do"),
            Category("reminder", "an event with a date or time"),
            Category("idea", "an idea, reflection or insight"),
        ]
    )
    todos = classifier.classify("Buy milk, call the plumber and finish the report.")
    assert todos.label == "to_do"

    reminder = classifier.classify("Remember: dentist appointment next Tuesday at 9 am.")
    assert reminder.label == "reminder"
