"""`laya_router.cli` — the ``laya-router`` command line."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .categories import load_labels
from .classifier import Classifier
from .metrics import evaluate, load_dataset


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="laya-router", description="Generic text-to-label router."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    classify = sub.add_parser("classify", help="Classify one text against a labels file.")
    classify.add_argument(
        "--labels", required=True, help="YAML file with `labels: {name: description}`."
    )
    classify.add_argument("--text", required=True, help="The text to classify.")
    classify.add_argument("--threshold", type=float, default=0.0)
    classify.add_argument("--top-k", type=int, default=None)

    measure = sub.add_parser("evaluate", help="Measure accuracy over a labelled JSONL dataset.")
    measure.add_argument("--labels", required=True)
    measure.add_argument("--dataset", required=True, help="JSONL with {text, label} per line.")
    measure.add_argument("--threshold", type=float, default=0.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns a process exit code."""
    args = _build_parser().parse_args(argv)
    categories = load_labels(args.labels)
    classifier = Classifier(categories, threshold=args.threshold)

    if args.command == "classify":
        result = classifier.classify(args.text)
        print(
            json.dumps(
                {
                    "label": result.label,
                    "confidence": result.confidence,
                    "below_threshold": result.below_threshold,
                    "scores": result.scores,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "evaluate":
        evaluation = evaluate(classifier, load_dataset(args.dataset))
        print(json.dumps(evaluation.as_dict(), ensure_ascii=False, indent=2))
        return 0

    return 2  # pragma: no cover - argparse enforces a known command


if __name__ == "__main__":
    sys.exit(main())
