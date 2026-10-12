"""CodeXchange: translate code between programming languages with Gemini.

Run with: streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st

from codexchange.languages import LANGUAGES
from codexchange.translator import DEFAULT_MODEL, GeminiTranslator, TranslationError

st.set_page_config(page_title="CodeXchange", page_icon="🔁", layout="wide")

state = st.session_state
state.setdefault("source_lang", "Python")
state.setdefault("target_lang", "JavaScript")
state.setdefault("source_code", "")
state.setdefault("result", None)  # (Translation, target language name)
state.setdefault("error", None)


def _secret(name: str) -> str | None:
    try:
        return st.secrets.get(name)
    except Exception:  # no secrets.toml configured
        return None


with st.sidebar:
    st.header("Settings")
    key_input = st.text_input("Gemini API key", type="password",
                              help="Kept only for this browser session. "
                                   "Alternatively set GEMINI_API_KEY.")
    model = st.text_input("Model", value=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    st.caption("[Get a Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)")

api_key = key_input or _secret("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")


def translate() -> None:
    # Runs as a button callback, i.e. before the page re-renders, so the result appears on
    # the same click instead of the next one.
    state.error = None
    try:
        translator = GeminiTranslator(api_key=api_key, model=model or None)
        state.result = (translator.translate(state.source_code, state.source_lang,
                                             state.target_lang), state.target_lang)
    except (ValueError, TranslationError) as exc:
        state.result = None
        state.error = str(exc)


def swap() -> None:
    state.source_lang, state.target_lang = state.target_lang, state.source_lang
    if state.result is not None:
        # Swapping after a translation continues from it, so a round trip is two clicks.
        state.source_code = state.result[0].code
        state.result = None


st.title("CodeXchange")
st.caption("Translate code between 12 languages with Gemini. Translation quality is measured "
           "by running the translated code; see the README.")

names = list(LANGUAGES)
left, middle, right = st.columns([12, 1, 12], vertical_alignment="top")

with left:
    st.selectbox("From", names, key="source_lang")
    st.text_area("Source code", key="source_code", height=420,
                 placeholder="Paste the code to translate…")

with middle:
    st.write("")
    st.write("")
    st.button("⇄", key="swap", on_click=swap, help="Swap languages")

with right:
    st.selectbox("To", names, key="target_lang")
    if state.result is not None:
        translation, target = state.result
        st.code(translation.code, language=LANGUAGES[target].fence, line_numbers=True)
        st.download_button("Download", data=translation.code,
                           file_name=f"translated.{LANGUAGES[target].extension}")
        st.caption(f"Translated by `{translation.model}`")
    else:
        st.info("The translation will appear here.")

st.button("Translate", key="translate", type="primary", on_click=translate)
if state.error:
    st.error(state.error)

with st.expander("How it works"):
    st.markdown(
        "- Your code and the two languages go to Gemini with a system prompt that asks for an "
        "exact behavioural translation, calling out the classic traps: negative modulo and "
        "floor division, rounding, sort order, string handling.\n"
        "- The reply's code block is extracted and shown with syntax highlighting.\n"
        "- `evals/` checks translations by **executing** them against test cases in the "
        "target language, because translated code that reads correctly can still behave "
        "differently."
    )
