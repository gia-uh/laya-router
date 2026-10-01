# laya-router — design

> Status: **design**. `laya-router` is a generic, domain-free text-to-label
> router built on [Laya](https://huggingface.co/convaiinnovations/laya).

## 1. What it is

`laya-router` answers one question: **given a text and a set of labelled
categories, which category fits best, and how sure is that?** It is a small
library and CLI on top of Laya (a non-autoregressive System 1 decision model):
Laya scores the options in a single forward pass and returns **calibrated
probabilities**.

`laya-router` knows **nothing about its consumer**: no audio, pipelines, tickets
or any domain. It only sees `text` and `categories` (as data). The consumer
decides what to do with the label (execute a pipeline, route a ticket, triage an
email…). This mirrors `legio`'s rule: the domain lives in the consumer's data,
never in this library.

## 2. Boundary

| Concern | Owner |
| --- | --- |
| Loading Laya, inference, threshold, top-k, metrics | `laya-router` |
| Defining categories and their descriptions | the consumer |
| What to do with the label / the low-confidence case | the consumer |
| Domain (audio, pipelines, CRM, intent…) | never `laya-router` |

## 3. Vocabulary

- **label** — one category name (a string key).
- **category** — a label plus the description Laya uses to score it.
- **classification** — the result: the best label, its calibrated probability,
  the full score ranking, and whether it fell below the threshold.
- **engine** — the inference backend (Laya in production; injectable in tests).

## 4. API

### Library

```python
from laya_router import Classifier, Category

clf = Classifier(
    categories=[
        Category("to_do", "a list of tasks to do"),
        Category("reminder", "events with dates or times"),
    ],
    threshold=0.6,
)
result = clf.classify("Call Ana tomorrow about the invoice")
# Classification(label="reminder", confidence=0.83, below_threshold=False,
#                scores={"reminder": 0.83, "to_do": 0.17}, ...)
```

- `classify(text, *, top_k=None)` returns a `Classification`.
- The **engine is injected** (`Classifier(engine=...)`); the default builds the
  Laya engine lazily so importing the package never downloads a model.
- `below_threshold` is **informative**: the classifier always returns the best
  label plus the flag; the consumer decides (menu, fallback, ask again…).

### Categories as data

```yaml
# labels.yaml — the consumer's data
labels:
  to_do: "a list of tasks to do"
  reminder: "events with dates or times"
  idea: "an idea or reflection to capture"
```

### CLI

```bash
laya-router classify --labels labels.yaml --text "…" [--top-k 3] [--threshold 0.6]
laya-router evaluate --labels labels.yaml --dataset eval.jsonl [--threshold 0.6]
```

- `classify` prints the classification as JSON.
- `evaluate` reports **accuracy**, the **confusion matrix** and the
  **threshold↔coverage** curve over a labelled dataset.

## 5. Evaluation dataset

A JSONL file, one object per line, domain-free:

```jsonl
{"text": "Call Ana tomorrow about the invoice", "label": "reminder"}
{"text": "Buy milk and bread", "label": "to_do"}
```

`evaluate` is the tool that turns "it looks right" into a number; it is part of
the library, not an afterthought.

## 6. Repository layout

```
laya-router/
  LICENSE                  # MIT
  README.md
  pyproject.toml           # uv, Python 3.13, ruff + pyright + pytest
  Makefile                 # make ci
  .github/workflows/ci.yml
  src/laya_router/
    __init__.py
    categories.py          # Category + loading labels.yaml
    engine.py              # Engine protocol, LayaEngine, FakeEngine (tests)
    classifier.py          # Classifier -> Classification
    metrics.py             # accuracy, confusion matrix, threshold sweep
    cli.py
  tests/
  docs/DESIGN.md
  docs/JOURNALS/
```

## 7. Baselines and non-goals

- **Not a service** in v1: a library plus CLI. A future adapter can wrap Laya's
  own `laya-serve` HTTP surface.
- **No domain**: no import of any consumer repo.
- **No generation**: Laya never generates text, so there is nothing to parse and
  no invented labels; the answer space is exactly the given categories.
- **Engine injection** keeps the fast test suite free of model downloads; the
  slow, real-Laya path is opt-in.

## 8. Risks

- **Laya is new** (Sep 2026). Evaluation is a first-class feature for that reason.
- **CPU latency**: Laya's `~33 ms` figures are GPU; the README reports
  `193–464 ms` preloaded on CPU. Real latency must be measured on the target host.
- **Zero-shot may be weak** on some label sets (the authors report 0.362 base on
  their typed-decisions benchmark); fine-tuning in the consumer's domain is the
  documented path, out of scope here.
- **Overlapping categories** (a meeting also has to-dos): the classification
  exposes the full `scores` ranking, so a consumer can act on top-k instead of
  pretending the labels are mutually exclusive.

## 9. Versioning

The public surface is `Classifier`, `Classification`, `Category`, the label
loader, `metrics` and the CLI. `laya` is an implementation detail behind the
`Engine` seam; the package's own API does not leak Laya's types.
