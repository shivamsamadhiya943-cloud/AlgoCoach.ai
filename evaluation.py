"""Run the labeled buggy submissions against AlgoCoach's fixed tests."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app import PROBLEMS, run_submission

ROOT = Path(__file__).resolve().parent
BENCHMARK = json.loads((ROOT / "benchmark.json").read_text(encoding="utf-8"))


def main() -> None:
    by_id = {p["id"]: p for p in PROBLEMS}
    results = []
    by_problem = Counter()
    for item in BENCHMARK:
        outcome = run_submission(item["code"], by_id[item["problem"]])
        caught = bool(outcome.get("ok") and any(not t["passed"] for t in outcome["results"]))
        by_problem[item["problem"]] += int(caught)
        results.append({"id": item["id"], "problem": item["problem"],
                        "actual_bug": item["actual_bug"], "caught_by_fixed_suite": caught,
                        "runner_error": outcome.get("error") if not outcome.get("ok") else None})

    caught_count = sum(r["caught_by_fixed_suite"] for r in results)
    report = {
        "benchmark_submissions": len(results),
        "known_bug_submissions_caught": caught_count,
        "fixed_suite_bug_detection_rate": round(caught_count / len(results), 4) if results else None,
        "by_problem_caught": dict(by_problem),
        "scope_note": "This measures whether the fixed tests expose incorrect outputs. It does not measure exact diagnosis accuracy, hint quality, or security.",
        "details": results,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
