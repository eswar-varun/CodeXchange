# CodeXchange

[![CI](https://github.com/eswar-varun/CodeXchange/actions/workflows/ci.yml/badge.svg)](https://github.com/eswar-varun/CodeXchange/actions/workflows/ci.yml)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-API-8E75B2?logo=googlegemini&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Translate code between 12 programming languages with Gemini, and measure translation quality
by **running** the translated code.

LLM translations usually *read* correctly. The failures that matter are the ones that don't
look wrong: `-1 % 5` is `4` in Python and `-1` in JavaScript; `[10, 9, 1].sort()` in
JavaScript gives `[1, 10, 9]`; Python's `round(2.5)` is `2`. CodeXchange includes an
execution-based evaluation built around exactly these traps.

## Features

- **12 languages:** Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, Kotlin, Swift,
  Ruby, PHP.
- **Faithful by design:** the system prompt asks for an exact behavioural translation and
  names the classic semantic traps. Temperature is kept low for the most likely answer.
- **Robust output handling:** the code block is extracted from the reply even when the model
  adds prose or several blocks.
- **Clean UI:** swap languages (a round trip is two clicks), download with the right file
  extension, and clear errors for missing keys, empty input, oversize input and API failures.
- **Execution-based evaluation:** see below.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GEMINI_API_KEY=...              # or paste it into the app's sidebar
streamlit run app.py
```

Get a key from [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key). The model
defaults to `gemini-3.8-flash`; override it in the sidebar or with `GEMINI_MODEL`.

## Evaluation: does the translation *behave* the same?

[`evals/tasks.json`](evals/tasks.json) holds 12 small functions. Each has a Python version, a
JavaScript version with **identical behaviour**, test cases, and the trap a plausible
translation falls into:

| Task | Trap |
|---|---|
| `wrap_index` | `%` sign rules differ for negative numbers |
| `bucket` | `//` floors; truncating division rounds toward zero |
| `sort_numbers` | JavaScript's default sort compares numbers as strings |
| `round_half` | Python rounds halves to even; `Math.round` rounds them up |
| `word_counts` | `split()` vs `split(' ')` on repeated whitespace |
| `top_k_frequent` | JavaScript object keys turn numbers into strings |
| `merge_intervals` | sorting pairs without a comparator |
| `title_case` | `str.title()` capitalises after apostrophes (`Bill'S`) |
| `is_palindrome`, `run_length_encode`, `roman_to_int`, `binary_search` | edge cases: empty input, end of string, subtractive pairs, integer midpoint |

The harness translates each task, **executes** the result in the target runtime against the
cases, and compares outputs after a JSON round trip:

```bash
python -m evals.run_eval --direction python-javascript              # current prompt (v2)
python -m evals.run_eval --direction python-javascript --prompt v1  # the original 2024 prompt
python -m evals.run_eval --direction javascript-python
python -m evals.run_eval --reference                                # no API: validates the tasks
```

The original 2024 prompt is kept as `v1`, so the effect of the rewrite is measured, not
assumed. Results are written to `evals/results/`.

CI runs the reference mode on every push. That proves each JavaScript reference matches its
Python twin case for case, and that the harness passes correct code. The test suite also
feeds it plausible but wrong translations (`Math.round`, `.sort()`, `split(' ')`, …) and
checks that each one is caught.

### Running model-generated code safely

The harness executes code a model wrote. Each run gets a fresh temporary directory and a
10-second timeout. Python runs in isolated mode (`-I`). Node runs under its
[permission model](https://nodejs.org/api/permissions.html): the code can read only its own
directory, and cannot write files or spawn processes (both covered by tests). That's a
mitigation, not a sandbox. Run large or untrusted evaluations in a container.

## Tests

```bash
pip install -r requirements-dev.txt
pytest          # 42 tests
ruff check .
```

| Area | How |
|---|---|
| Translator | fake Gemini client: prompts, config, input validation, API failures, empty replies, code extraction |
| Evaluation harness | reference solutions in both directions, plausible wrong translations, syntax errors, missing entry points, infinite loops, sandbox escapes |
| UI | the real Streamlit script driven headlessly with `AppTest`: rendering, the missing-key path, same-click results, swap |

## History

CodeXchange started in July 2024 on Google's PaLM API (`chat-bison-001`). The original
project reports are in [`docs/project-reports/`](docs/project-reports) and a demo of that
version is in [`docs/demo.mp4`](docs/demo.mp4). Google later shut the PaLM API down, so in
2026 the app was rebuilt on the Gemini API, with tests and the execution-based evaluation
added.

## License

MIT
