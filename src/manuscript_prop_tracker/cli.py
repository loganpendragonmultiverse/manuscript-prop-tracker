from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import evaluate, load_tracker, render_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check manuscript prop continuity.")
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--compare-from", help="Compare states from this milestone; requires --through"
    )
    parser.add_argument("--through", help="Stop after this milestone")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(load_tracker(args.input), args.through, compare_from=args.compare_from)
        rendered = (
            json.dumps(report, indent=2, ensure_ascii=False) + "\n"
            if args.format == "json"
            else render_markdown(report)
        )
        if args.output:
            if args.output.exists():
                raise ValueError(f"output already exists: {args.output}")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
