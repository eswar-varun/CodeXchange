"""Execute code in Python or JavaScript against test cases and compare results.

A translation that *reads* right can still *behave* differently (negative modulo, rounding,
sort order, ...), so translations are judged by running them. Results are compared after a
JSON round trip, which is the contract between the two languages: a dict and a plain object
match, a tuple and a list match, a JavaScript Map does not.

This runs model-generated code. Each run gets a fresh temporary directory and a timeout.
Python runs in isolated mode (-I). Node runs under its permission model, so the code
can read only its own directory and cannot write files or spawn processes. That is a
mitigation, not a sandbox: run untrusted evaluations in a container.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TASKS_FILE = Path(__file__).with_name("tasks.json")
TIMEOUT_S = 10
RUNTIMES = ("python", "javascript")

_PY_DRIVER = """\
import json, sys
names, cases = json.loads(sys.argv[2]), json.load(open(sys.argv[3], encoding="utf-8"))
namespace = {"__name__": "solution"}
try:
    exec(compile(open(sys.argv[1], encoding="utf-8").read(), "solution.py", "exec"), namespace)
except Exception as exc:
    print(json.dumps({"error": f"failed to load: {type(exc).__name__}: {exc}"})); sys.exit()
fn = next((namespace[n] for n in names if callable(namespace.get(n))), None)
if fn is None:
    print(json.dumps({"error": f"no function named {' or '.join(names)}"})); sys.exit()
results = []
for case in cases:
    try:
        results.append({"value": fn(*case["args"])})
    except Exception as exc:
        results.append({"raised": f"{type(exc).__name__}: {exc}"})
print(json.dumps({"results": results}, default=repr))
"""

_JS_DRIVER = """\
const fs = require("fs");
const [file, namesJson, casesFile] = process.argv.slice(2);
const names = JSON.parse(namesJson);
const cases = JSON.parse(fs.readFileSync(casesFile, "utf8"));
// Translations sometimes add module syntax; strip it so the code runs as a plain script.
const code = fs.readFileSync(file, "utf8")
  .replace(/^\\s*export\\s+(default\\s+)?/gm, "")
  .replace(/^\\s*module\\.exports\\s*=.*$/gm, "");
const pick = names.map(n => `typeof ${n} === "function" ? ${n} : `).join("") + "undefined";
let fn;
try {
  fn = new Function(`${code}\\nreturn ${pick};`)();
} catch (e) {
  console.log(JSON.stringify({ error: `failed to load: ${e}` })); process.exit(0);
}
if (!fn) {
  console.log(JSON.stringify({ error: `no function named ${names.join(" or ")}` }));
  process.exit(0);
}
const results = cases.map(c => {
  try { return { value: fn(...structuredClone(c.args)) }; }
  catch (e) { return { raised: String(e) }; }
});
console.log(JSON.stringify({ results }));
"""


@dataclass
class TaskResult:
    task_id: str
    passed: bool
    detail: str = ""
    failures: list[dict[str, Any]] = field(default_factory=list)


def load_tasks(path: Path = TASKS_FILE) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def entry_names(task: dict[str, Any]) -> list[str]:
    """Accept either language's naming convention: wrap_index or wrapIndex."""
    names = [task["python"]["entry"], task["javascript"]["entry"]]
    return list(dict.fromkeys(names))


def run(code: str, runtime: str, task: dict[str, Any]) -> TaskResult:
    if runtime not in RUNTIMES:
        raise ValueError(f"cannot execute {runtime!r}; supported: {RUNTIMES}")
    with tempfile.TemporaryDirectory(prefix="codexchange-eval-") as tmp:
        work = Path(tmp)
        ext, driver = ("py", _PY_DRIVER) if runtime == "python" else ("js", _JS_DRIVER)
        (work / f"solution.{ext}").write_text(code, encoding="utf-8")
        (work / f"driver.{ext}").write_text(driver, encoding="utf-8")
        (work / "cases.json").write_text(json.dumps(task["cases"]), encoding="utf-8")
        args = [str(work / f"solution.{ext}"), json.dumps(entry_names(task)),
                str(work / "cases.json")]
        command = _command(runtime, work, ext) + args
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_S,  # noqa: S603
                                  cwd=work, encoding="utf-8")
        except subprocess.TimeoutExpired:
            return TaskResult(task["id"], False, f"timed out after {TIMEOUT_S}s")
    return _judge(task, proc)


def _command(runtime: str, work: Path, ext: str) -> list[str]:
    if runtime == "python":
        return [sys.executable, "-I", str(work / f"driver.{ext}")]
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("node is required to execute JavaScript")
    return [node, "--permission", f"--allow-fs-read={work}", str(work / f"driver.{ext}")]


def _judge(task: dict[str, Any], proc: subprocess.CompletedProcess[str]) -> TaskResult:
    lines = proc.stdout.strip().splitlines()
    try:
        report = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        stderr = proc.stderr.strip().splitlines()
        return TaskResult(task["id"], False, f"crashed: {stderr[-1] if stderr else 'no output'}")
    if "error" in report:
        return TaskResult(task["id"], False, report["error"])

    failures = []
    for case, outcome in zip(task["cases"], report["results"], strict=True):
        # Compare through JSON so both runtimes' values are judged on the same terms.
        actual = json.loads(json.dumps(outcome.get("value"))) if "value" in outcome else None
        if "raised" in outcome or actual != case["expected"]:
            failures.append({"args": case["args"], "expected": case["expected"],
                             "actual": outcome.get("raised", actual)})
    if failures:
        first = failures[0]
        detail = (f"{len(failures)}/{len(task['cases'])} cases wrong, e.g. "
                  f"args={first['args']} expected={first['expected']!r} got={first['actual']!r}")
        return TaskResult(task["id"], False, detail, failures)
    return TaskResult(task["id"], True)
