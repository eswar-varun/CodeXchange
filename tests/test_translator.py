from __future__ import annotations

from types import SimpleNamespace

import pytest

from codexchange import languages
from codexchange.translator import (
    MAX_SOURCE_CHARS,
    PROMPTS,
    GeminiTranslator,
    MissingAPIKeyError,
    TranslationError,
    build_prompt,
    extract_code,
)


class FakeModels:
    def __init__(self, reply: str = "```javascript\nconsole.log(1);\n```", error=None):
        self.reply, self.error, self.calls = reply, error, []

    def generate_content(self, *, model, contents, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.reply)


def _translator(**kwargs):
    models = FakeModels(**kwargs)
    return GeminiTranslator(client=SimpleNamespace(models=models), model="test-model"), models


# --- extract_code --------------------------------------------------------------------------


@pytest.mark.parametrize(("reply", "expected"), [
    ("```python\nprint(1)\n```", "print(1)"),
    ("```\nprint(1)\n```", "print(1)"),
    ("Here you go:\n```js\nlet a = 1;\n```\nHope that helps!", "let a = 1;"),
    ("```js\nmain();\n```\n```js\nfunction main() {\n  return 42;\n}\n```",
     "function main() {\n  return 42;\n}"),
    ("print(1)", "print(1)"),
    ("```python\r\nprint(1)\r\n```", "print(1)"),
], ids=["tagged", "untagged", "prose-around", "longest-block-wins", "no-fence", "crlf"])
def test_extract_code(reply, expected):
    assert extract_code(reply) == expected


def test_extract_code_does_not_leak_the_language_tag():
    # The 2024 version sliced [3:-4] off the reply, which left "python\n" in the output.
    assert not extract_code("```python\nx = 1\n```").startswith("python")


# --- build_prompt --------------------------------------------------------------------------


def test_prompt_names_both_languages_and_fences_the_source():
    prompt = build_prompt("  x = 1  \n", languages.get("Python"), languages.get("Go"))
    assert prompt.startswith("Translate this Python code to Go.")
    assert "```python\nx = 1\n```" in prompt


# --- GeminiTranslator ----------------------------------------------------------------------


def test_translate_sends_model_prompt_and_system_instruction():
    translator, models = _translator()

    result = translator.translate("print(1)", "Python", "JavaScript")

    assert result.code == "console.log(1);"
    assert result.model == "test-model"
    (call,) = models.calls
    assert call["model"] == "test-model"
    assert "Translate this Python code to JavaScript." in call["contents"]
    assert "idiomatic JavaScript" in call["config"].system_instruction
    assert call["config"].temperature == pytest.approx(0.1)


def test_prompt_version_is_selectable():
    translator, models = _translator()
    translator.prompt = "v1"
    translator.translate("print(1)", "Python", "Go")
    assert models.calls[0]["config"].system_instruction == PROMPTS["v1"].format(target="Go")


def test_unknown_prompt_version_is_rejected():
    with pytest.raises(ValueError, match="unknown prompt"):
        GeminiTranslator(client=SimpleNamespace(models=FakeModels()), prompt="v9")


@pytest.mark.parametrize(("code", "source", "target", "message"), [
    ("   ", "Python", "Go", "Enter some code"),
    ("x = 1", "Python", "Python", "the same"),
    ("x" * (MAX_SOURCE_CHARS + 1), "Python", "Go", "limit"),
    ("x = 1", "Python", "COBOL", "unsupported language"),
])
def test_invalid_requests_never_reach_the_model(code, source, target, message):
    translator, models = _translator()
    with pytest.raises(ValueError, match=message):
        translator.translate(code, source, target)
    assert models.calls == []


def test_api_failures_become_translation_errors():
    translator, _ = _translator(error=RuntimeError("503 overloaded"))
    with pytest.raises(TranslationError, match="503 overloaded"):
        translator.translate("x = 1", "Python", "Go")


def test_empty_reply_is_an_error_not_an_empty_translation():
    translator, _ = _translator(reply="   ")
    with pytest.raises(TranslationError, match="empty response"):
        translator.translate("x = 1", "Python", "Go")


def test_missing_api_key_is_reported(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError):
        GeminiTranslator()


def test_model_can_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "env-model")
    assert GeminiTranslator(client=SimpleNamespace(models=FakeModels())).model == "env-model"
