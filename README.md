# laya-router

A generic, **domain-free** text-to-label router built on
[Laya](https://huggingface.co/convaiinnovations/laya), a non-autoregressive
System 1 decision model.

Given a **text** and a set of **labelled categories** (your data), `laya-router`
returns the best-fitting label with a **calibrated probability** — in a single
forward pass, with no text generation and therefore no parsing and no invented
labels.

It knows nothing about its consumers: no audio, pipelines, tickets or any other
domain. The categories are data; the label is yours to act on.

## Why

- **The answer space is exactly your categories** — Laya scores the options you
  give it; it cannot invent a label that is not in the set.
- **Calibrated confidence** — decide a threshold (e.g. "below 0.6, ask the
  user"), something generative routers cannot give you reliably.
- **Fast and cheap** — one forward pass; no per-token cost, no provider, no
  rate limits.
- **Multilingual** — the default checkpoint (`multilingual`) covers 100+ languages.

## Install

```bash
uv sync          # install dependencies
uv pip install -e .
```

Requires Python 3.13. The first real classification downloads the Laya
checkpoint (~650 MB) once; importing the package never does.

## Library

```python
from laya_router import Category, Classifier

classifier = Classifier(
    categories=[
        Category("to_do", "a list of tasks to do"),
        Category("reminder", "an event with a date or time"),
        Category("idea", "an idea, reflection or insight"),
    ],
    threshold=0.6,
)
result = classifier.classify("Remember: dentist next Tuesday at 9 am.")
# Classification(label='reminder', confidence=0.83, below_threshold=False, ...)
print(result.label, result.confidence, result.below_threshold)
print(result.ranked(top_k=3))  # the full ranking, useful for overlapping categories
```

`below_threshold` is **informative**: the classifier always returns the best
label plus the flag; your code decides what to do with a weak answer.

> **Out-of-scope texts.** Laya picks the best of the labels you give it, so a
> text that fits none of them still gets *a* label (a question about the weather
> may land on your closest option with moderate confidence). Use `threshold` to
> catch those: a text whose confidence falls below it is flagged
> `below_threshold=True`, and you can ask again or refuse.

## Measured on CPU

Real numbers from this project on a laptop CPU (multilingual checkpoint, warm):

| Text | Label | Confidence | Latency |
| --- | --- | --- | --- |
| "buy milk, call the plumber, finish the report" | `to_do` | 0.997 | ~116 ms |
| "remind me: dentist on Tuesday at 9" | `reminder` | 1.000 | ~112 ms |
| "I had an idea for organising voice notes" | `idea` | 1.000 | ~119 ms |

The first call loads the checkpoint (seconds); later calls are ~110–130 ms.

## Categories as data

```yaml
# labels.yaml — supplied by the consumer, never by this library
labels:
  to_do: "a list of tasks to do"
  reminder: "an event with a date or time"
  idea: "an idea, reflection or insight"
```

## CLI

```bash
laya-router classify --labels labels.yaml --text "Remember: dentist Tuesday at 9 am."
laya-router evaluate --labels labels.yaml --dataset eval.jsonl
```

`evaluate` reports **accuracy**, the **confusion matrix** and a
**threshold↔coverage** curve over a labelled JSONL dataset
(`{"text": ..., "label": ...}` per line). It is the tool that turns "it looks
right" into a number.

## Development

```bash
make ci                # fast gate: ruff + format + pyright + unit tests (no model)
make test-integration  # real Laya checkpoints (downloads the model; slow on CPU)
```

The fast suite injects a fake engine, so it needs no model and stays
deterministic.

## Design

See [`docs/DESIGN.md`](docs/DESIGN.md).

## License

MIT — see [LICENSE](LICENSE). © 2026 GIA-UH and Syalia S.R.L.
