from __future__ import annotations

import argparse
import json
from pathlib import Path

from watchlight.evals.dataset import load_dataset
from watchlight.evals.runner import EvalRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a labelled Watchlight snapshot dataset")
    parser.add_argument("dataset", type=Path, help="JSONL dataset path")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evals/reports"),
        help="directory for JSON and Markdown reports",
    )
    args = parser.parse_args()
    report = EvalRunner().run(load_dataset(args.dataset))
    json_path, markdown_path = report.write(args.output_dir)
    print(json.dumps(report.metrics, ensure_ascii=False, indent=2))
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
