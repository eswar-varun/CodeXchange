"""Translate every task and check the result by running it.

    python -m evals.run_eval --direction python-javascript
    python -m evals.run_eval --direction javascript-python --prompt v1   # the 2024 prompt
    python -m evals.run_eval --reference   # no API call: validates the tasks and harness

Needs GEMINI_API_KEY (except with --reference) and Node.js for JavaScript.
Results go to evals/results/<timestamp>.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from codexchange.translator import DEFAULT_PROMPT, PROMPTS, GeminiTranslator, TranslationError

from .harness import TaskResult, load_tasks, run

DIRECTIONS = {"python-javascript": ("python", "javascript"),
              "javascript-python": ("javascript", "python")}
DISPLAY = {"python": "Python", "javascript": "JavaScript"}
RESULTS_DIR = Path(__file__).with_name("results")


def evaluate(direction: str, *, reference: bool = False, model: str | None = None,
             prompt: str = DEFAULT_PROMPT) -> list[TaskResult]:
    source, target = DIRECTIONS[direction]
    translator = None if reference else GeminiTranslator(model=model, prompt=prompt)
    results = []
    for task in load_tasks():
        if translator is None:
            code = task[target]["code"]  # the known-good answer: validates tasks and harness
        else:
            try:
                code = translator.translate(task[source]["code"], DISPLAY[source],
                                            DISPLAY[target]).code
            except TranslationError as exc:
                results.append(TaskResult(task["id"], False, f"translation failed: {exc}"))
                continue
        results.append(run(code, target, task))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--direction", choices=sorted(DIRECTIONS), default="python-javascript")
    parser.add_argument("--prompt", choices=sorted(PROMPTS), default=DEFAULT_PROMPT)
    parser.add_argument("--model", default=None)
    parser.add_argument("--reference", action="store_true",
                        help="use the reference solutions instead of calling the model")
    args = parser.parse_args()

    results = evaluate(args.direction, reference=args.reference, model=args.model,
                       prompt=args.prompt)
    passed = sum(r.passed for r in results)
    variant = "reference" if args.reference else args.prompt
    label = variant if args.reference else f"{args.model or 'default model'}, prompt {variant}"

    print("| task | result | detail |\n|---|---|---|")
    for r in results:
        print(f"| {r.task_id} | {'pass' if r.passed else 'FAIL'} | {r.detail} |")
    print(f"\n**{args.direction} ({label}): {passed}/{len(results)} tasks pass**")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{stamp}-{args.direction}-{variant}.json"
    out.write_text(json.dumps({"direction": args.direction, "label": label, "passed": passed,
                               "total": len(results), "results": [asdict(r) for r in results]},
                              indent=2), encoding="utf-8")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
