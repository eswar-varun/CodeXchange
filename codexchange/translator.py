"""Translate code between languages with Gemini.

The model is reached through a small client interface (anything with
`.models.generate_content(...)`), so tests and the evaluation harness can substitute a fake
and nothing here needs a network connection to be tested.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Protocol

from .languages import Language, get

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_SOURCE_CHARS = 20_000  # bounds cost per request; a whole file, not a whole repo

# System prompts by version. "v1" is the 2024 original, kept so the evaluation can measure
# whether the rewrite actually helps (evals/run_eval.py --prompt v1).
PROMPTS = {
    "v1": (
        "You are a highly skilled software developer with expertise in multiple programming "
        "languages. Translate the following code to {target}. Ensure that the functionality "
        "remains the same and that you follow best practices and idioms of the {target} "
        "language. Give only the code, no explanations."
    ),
    "v2": """You are an expert software engineer who translates code between programming \
languages.

Rules:
- Preserve behaviour exactly, including edge cases: integer division and modulo of negative \
numbers, rounding, sorting order, string handling, and error cases.
- Write idiomatic {target} that follows its conventions and standard library.
- Keep the same function and class names, adjusted only to {target}'s naming convention.
- Do not add explanations, example usage, or a main function unless the source has one.
- Reply with exactly one fenced code block and nothing else.""",
}
DEFAULT_PROMPT = "v2"

_FENCED = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)


class TranslationError(Exception):
    """The model call failed or returned nothing usable."""


class MissingAPIKeyError(TranslationError):
    pass


class _Models(Protocol):
    def generate_content(self, *, model: str, contents: Any, config: Any = None) -> Any: ...


class _Client(Protocol):
    models: _Models


@dataclass(frozen=True)
class Translation:
    code: str
    model: str
    raw_response: str


def build_prompt(code: str, source: Language, target: Language) -> str:
    return (f"Translate this {source.name} code to {target.name}.\n\n"
            f"```{source.fence}\n{code.strip()}\n```")


def extract_code(response_text: str) -> str:
    """Pull the code out of a model reply.

    Models usually comply with "one fenced block", but sometimes add prose around it or
    split the answer. Take the longest fenced block (the solution, not a usage snippet);
    with no fence at all, assume the whole reply is code.
    """
    text = response_text.replace("\r\n", "\n")
    blocks = _FENCED.findall(text)
    code = max(blocks, key=len) if blocks else text
    return code.strip("\n")


class GeminiTranslator:
    def __init__(self, *, api_key: str | None = None, model: str | None = None,
                 prompt: str = DEFAULT_PROMPT, client: _Client | None = None) -> None:
        if prompt not in PROMPTS:
            raise ValueError(f"unknown prompt version {prompt!r}; choose from {sorted(PROMPTS)}")
        self.prompt = prompt
        self.model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
        if client is None:
            key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not key:
                raise MissingAPIKeyError(
                    "No Gemini API key. Set GEMINI_API_KEY or enter one in the sidebar.")
            from google import genai  # imported lazily so tests don't need credentials

            client = genai.Client(api_key=key)
        self._client = client

    def translate(self, code: str, source_name: str, target_name: str) -> Translation:
        source, target = get(source_name), get(target_name)
        if not code.strip():
            raise ValueError("Enter some code to translate.")
        if source == target:
            raise ValueError("Source and target languages are the same.")
        if len(code) > MAX_SOURCE_CHARS:
            raise ValueError(f"Source is {len(code):,} characters; the limit is "
                             f"{MAX_SOURCE_CHARS:,}. Translate it in smaller pieces.")

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=PROMPTS[self.prompt].format(target=target.name),
            temperature=0.1,  # translation wants the most likely answer, not creativity
        )
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=build_prompt(code, source, target), config=config)
        except Exception as exc:  # the SDK raises several error types; surface them all alike
            raise TranslationError(f"Gemini request failed: {exc}") from exc

        text = getattr(response, "text", None) or ""
        if not text.strip():
            raise TranslationError("Gemini returned an empty response (it may have been "
                                   "blocked by a safety filter). Try again or rephrase.")
        return Translation(extract_code(text), self.model, text)
