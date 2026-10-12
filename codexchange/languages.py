from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    name: str  # shown to people and used in the prompt
    fence: str  # Markdown code-fence tag; also the syntax-highlighting id Streamlit uses
    extension: str  # for the download button


LANGUAGES: dict[str, Language] = {
    lang.name: lang
    for lang in (
        Language("Python", "python", "py"),
        Language("JavaScript", "javascript", "js"),
        Language("TypeScript", "typescript", "ts"),
        Language("Java", "java", "java"),
        Language("C++", "cpp", "cpp"),
        Language("C#", "csharp", "cs"),
        Language("Go", "go", "go"),
        Language("Rust", "rust", "rs"),
        Language("Kotlin", "kotlin", "kt"),
        Language("Swift", "swift", "swift"),
        Language("Ruby", "ruby", "rb"),
        Language("PHP", "php", "php"),
    )
}


def get(name: str) -> Language:
    try:
        return LANGUAGES[name]
    except KeyError:
        raise ValueError(f"unsupported language: {name!r}") from None
