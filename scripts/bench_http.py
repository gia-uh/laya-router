"""Per-call latency of the ``laya-serve`` HTTP API over a labelled dataset.

Measures each request individually (cold vs warm: min/median/mean/max), the
total time and the accuracy, talking **HTTP only** — no library import. It is
the service-mode counterpart of the library's ``evaluate``.

Usage (with the service already up: `make serve-up`):

    uv run --with httpx python scripts/bench_http.py \
        --base-url http://127.0.0.1:8000 \
        --token dev-token \
        --labels examples/invox/labels.yaml \
        --dataset examples/invox/eval.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections.abc import Sequence
from pathlib import Path

import httpx
import yaml

QUESTION_NAME = "label"
INSTRUCTIONS = "Which category fits this text best?"


def load_labels(path: Path) -> dict[str, str]:
    """Read a ``labels: {name: description}`` YAML file into a criteria mapping."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(data["labels"])


def load_dataset(path: Path) -> list[dict[str, str]]:
    """Read a JSONL dataset of ``{"text": ..., "label": ...}`` rows."""
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def classify(
    client: httpx.Client, base_url: str, token: str, text: str, criteria: dict[str, str]
) -> tuple[str, float]:
    """One ``choice`` request; returns the chosen label and its confidence."""
    body = {
        "state": {"document": text},
        "questions": {
            QUESTION_NAME: {
                "type": "choice",
                "instructions": INSTRUCTIONS,
                "criteria": criteria,
            }
        },
    }
    response = client.post(
        f"{base_url.rstrip('/')}/v1/systemone",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    answer = response.json()["answers"][QUESTION_NAME]
    return answer["choice"], answer["answer_confidence"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure the laya-serve HTTP API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default="dev-token")
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    criteria = load_labels(args.labels)
    examples = load_dataset(args.dataset)

    with httpx.Client(timeout=args.timeout) as client:
        start = time.perf_counter()
        classify(client, args.base_url, args.token, "warm up", criteria)
        cold_ms = (time.perf_counter() - start) * 1000

        per_call: list[float] = []
        correct = 0
        for example in examples:
            start = time.perf_counter()
            label, _confidence = classify(
                client, args.base_url, args.token, example["text"], criteria
            )
            per_call.append((time.perf_counter() - start) * 1000)
            correct += int(label == example["label"])

    total_s = sum(per_call) / 1000
    print(f"cold call (first request): {cold_ms:.1f} ms")
    print(f"calls: {len(per_call)}")
    print(f"total for the dataset: {total_s:.2f} s")
    print(f"min    : {min(per_call):.1f} ms")
    print(f"median : {statistics.median(per_call):.1f} ms")
    print(f"mean   : {statistics.mean(per_call):.1f} ms")
    print(f"max    : {max(per_call):.1f} ms")
    print(f"accuracy: {correct}/{len(examples)} = {correct / len(examples):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
