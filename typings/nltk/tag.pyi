from __future__ import annotations

def pos_tag(
    tokens: list[str], tagset: str | None = None, lang: str = "eng"
) -> list[tuple[str, str]]: ...
