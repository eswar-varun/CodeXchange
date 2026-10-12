"""The evaluation harness is a test tool, so it gets tested too: it must pass correct code,
fail code that falls into each trap, and survive code that hangs, crashes or misbehaves."""

from __future__ import annotations

import shutil

import pytest

from evals.harness import load_tasks, run
from evals.run_eval import evaluate

TASKS = {t["id"]: t for t in load_tasks()}
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")


def test_every_task_has_both_references_and_cases():
    for task in TASKS.values():
        assert task["python"]["code"] and task["javascript"]["code"], task["id"]
        assert task["cases"], task["id"]
        assert task["trap"], task["id"]


@needs_node
@pytest.mark.parametrize("direction", ["python-javascript", "javascript-python"])
def test_reference_solutions_pass_every_task(direction):
    results = evaluate(direction, reference=True)
    assert [r.task_id for r in results if not r.passed] == []


# Plausible-looking translations that fall into each task's trap.
NAIVE_JS = {
    "wrap_index": "function wrapIndex(i, n) { return i % n; }",
    "bucket": "function bucket(value, size) { return Math.trunc(value / size); }",
    "sort_numbers": "function sortNumbers(nums) { return [...nums].sort(); }",
    "round_half": "function roundHalf(x) { return Math.round(x); }",
    "word_counts": """function wordCounts(text) {
        const c = {};
        for (const w of text.toLowerCase().split(' ')) c[w] = (c[w] || 0) + 1;
        return c;
    }""",
    "top_k_frequent": """function topKFrequent(nums, k) {
        const c = {};
        for (const n of nums) c[n] = (c[n] || 0) + 1;
        return Object.keys(c).sort((a, b) => c[b] - c[a]).slice(0, k);
    }""",
    "title_case": """function titleCase(s) {
        return s.split(' ').map(w => w[0].toUpperCase() + w.slice(1).toLowerCase()).join(' ');
    }""",
}


@needs_node
@pytest.mark.parametrize("task_id", sorted(NAIVE_JS))
def test_naive_translations_are_caught(task_id):
    result = run(NAIVE_JS[task_id], "javascript", TASKS[task_id])
    assert not result.passed
    assert "cases wrong" in result.detail


@pytest.mark.parametrize(("code", "detail"), [
    ("def wrong_name(i, n):\n    return i % n\n", "no function named"),
    ("def wrap_index(i, n)\n    return i % n\n", "failed to load: SyntaxError"),
    ("def wrap_index(i, n):\n    return i / 0\n", "cases wrong"),
])
def test_python_failures_are_reported_not_raised(code, detail):
    result = run(code, "python", TASKS["wrap_index"])
    assert not result.passed
    assert detail in result.detail


def test_either_naming_convention_is_accepted():
    camel = "def wrapIndex(i, n):\n    return i % n\n"
    assert run(camel, "python", TASKS["wrap_index"]).passed


def test_runaway_code_is_stopped(monkeypatch):
    monkeypatch.setattr("evals.harness.TIMEOUT_S", 2)
    result = run("def wrap_index(i, n):\n    while True:\n        pass\n", "python",
                 TASKS["wrap_index"])
    assert result.detail == "timed out after 2s"


@needs_node
def test_js_module_syntax_is_tolerated():
    code = "export function wrapIndex(i, n) { return ((i % n) + n) % n; }"
    assert run(code, "javascript", TASKS["wrap_index"]).passed


@needs_node
@pytest.mark.parametrize("attack", [
    "process.getBuiltinModule('child_process').execSync('echo pwned')",
    "process.getBuiltinModule('fs').writeFileSync('pwned.txt', 'x')",
], ids=["spawn-process", "write-file"])
def test_js_runs_under_node_permission_model(attack):
    code = f"function wrapIndex(i, n) {{ {attack}; return ((i % n) + n) % n; }}"
    result = run(code, "javascript", TASKS["wrap_index"])
    assert not result.passed
    assert all("Access to this API has been restricted" in str(f["actual"])
               for f in result.failures)


def test_unsupported_runtime_is_rejected():
    with pytest.raises(ValueError, match="cannot execute"):
        run("fn main() {}", "rust", TASKS["wrap_index"])
