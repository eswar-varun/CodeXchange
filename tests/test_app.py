"""UI tests: run the real Streamlit script headlessly with AppTest."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import codexchange.translator as translator_module
from codexchange.translator import Translation

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def test_page_renders_with_defaults():
    at = _app()
    assert not at.exception
    assert at.title[0].value == "CodeXchange"
    assert at.selectbox(key="source_lang").value == "Python"
    assert at.selectbox(key="target_lang").value == "JavaScript"


def test_translating_without_a_key_explains_what_to_do():
    at = _app()
    at.text_area(key="source_code").input("print(1)")
    at.button(key="translate").click().run()
    assert "No Gemini API key" in at.error[0].value


def test_successful_translation_is_shown_on_the_same_click(monkeypatch):
    class FakeTranslator:
        def __init__(self, **kwargs):
            pass

        def translate(self, code, source, target):
            return Translation(f"// {source} -> {target}\nconsole.log(1);", "fake-model", "")

    monkeypatch.setattr(translator_module, "GeminiTranslator", FakeTranslator)
    at = _app()
    at.text_area(key="source_code").input("print(1)")
    at.button(key="translate").click().run()

    assert not at.error
    assert at.code[0].value == "// Python -> JavaScript\nconsole.log(1);"


def test_swap_turns_the_translation_into_the_next_source(monkeypatch):
    class FakeTranslator:
        def __init__(self, **kwargs):
            pass

        def translate(self, code, source, target):
            return Translation("console.log(1);", "fake-model", "")

    monkeypatch.setattr(translator_module, "GeminiTranslator", FakeTranslator)
    at = _app()
    at.text_area(key="source_code").input("print(1)")
    at.button(key="translate").click().run()
    at.button(key="swap").click().run()

    assert at.selectbox(key="source_lang").value == "JavaScript"
    assert at.selectbox(key="target_lang").value == "Python"
    assert at.text_area(key="source_code").value == "console.log(1);"
