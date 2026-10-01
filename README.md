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

Real numbers from this project on a laptop CPU. The engine runs warm (the cold
start is a separate line).

**Short texts, library mode** (multilingual checkpoint):

| Text | Label | Confidence | Latency |
| --- | --- | --- | --- |
| "buy milk, call the plumber, finish the report" | `to_do` | 0.997 | ~116 ms |
| "remind me: dentist on Tuesday at 9" | `reminder` | 1.000 | ~112 ms |
| "I had an idea for organising voice notes" | `idea` | 1.000 | ~119 ms |

**Long texts, service mode** (`make bench-http` over the ten-label example in
`examples/invox/`, 21 texts of ~400 characters, HTTP to `laya-serve`):

| Metric | Value |
| --- | --- |
| Cold call (first request after start) | ~750–1500 ms |
| Min | ~330 ms |
| Median | ~560 ms |
| Mean | ~560 ms |
| Max | ~800 ms |
| Total (21 texts) | ~12 s |

Latency grows with the text length and the service adds the HTTP round trip;
the library path is faster because it skips it.

> **Accuracy is a property of the categories, not of the transport.** On the
> ten overlapping invox pipelines, zero-shot accuracy is around **0.5**; with
> three clear labels it is near 1.0. Overlapping categories and many options
> (`project_roadmap` vs `idea`, `to_do` vs `email_simple_draft`) are the hard
> cases. Use fewer options per call, tighten the descriptions, set a threshold,
> or fine-tune — see [Fine-tuning is the next step](#fine-tuning-is-the-next-step).

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
make test-integration  # real Laya with MODEL=… (needs `make models-pull`)
make help              # every command
```

The fast suite injects a fake engine, so it needs no model and stays
deterministic.

## Layout

```
src/laya_router/
  categories.py   # Category + labels.yaml loader (consumer data)
  engine.py       # Engine seam: LayaEngine (real) | FakeEngine (tests)
  classifier.py   # Classifier -> Classification (label, confidence, ranking)
  metrics.py      # accuracy, confusion matrix, threshold curve
  cli.py          # laya-router classify | evaluate
scripts/
  bench_http.py   # per-call latency + accuracy against a running laya-serve
examples/invox/   # a consumer example: ten labels + a labelled dataset
docs/
  DESIGN.md       # what it is, the boundary, the API
  SERVE.md        # the HTTP service: contract, command, environment
  JOURNALS/       # turn-by-turn development journal
```

## Run against the real model

The model is a **shared resource**: download it once, then both ways of using
the router read the same cache, offline.

```bash
make models-pull MODEL=multilingual   # english | multilingual | typed-decisions
make models-list                      # what is cached
make classify LABELS=labels.yaml TEXT="Call Ana tomorrow at 9"
```

## Run as a service

`laya-serve` (shipped by Laya) serves the same checkpoints over HTTP for any
language to consume. This project launches and documents it; it does not
reimplement it.

```bash
make serve-up       # start laya-serve (background) with MODEL and LAYA_API_KEY
make serve-smoke    # 401 without token, 200 with token, one real choice
make bench-http LABELS=examples/invox/labels.yaml DATASET=examples/invox/eval.jsonl
make serve-down
```

Then `POST /v1/systemone` with a `choice` question. Full details, the raw
command and the environment variables are in [`docs/SERVE.md`](docs/SERVE.md).

## Fine-tuning is the next step

Zero-shot routing between many overlapping categories is limited (see the
numbers above). The documented path is to fine-tune a checkpoint on labelled
examples from your domain — Laya reports a large jump (e.g. 0.36 → 0.77 on its
own benchmark). When that happens, **nothing in this project changes**: point
the service (or `LAYA_ROUTER_MODEL`) at the new checkpoint, and the contract and
the clients stay the same.

## Design

See [`docs/DESIGN.md`](docs/DESIGN.md) and [`docs/SERVE.md`](docs/SERVE.md).

## License

MIT — see [LICENSE](LICENSE). © 2026 GIA-UH and Syalia S.R.L.
