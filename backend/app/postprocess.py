from __future__ import annotations

from app.contracts import AppliedCorrection
from app.text_normalizer import normalize_text


def run_postprocess(
    raw_text: str,
    hotword_map: dict[str, str],
    punctuation_enabled: bool = True,
    spacing_enabled: bool = True,
    simplified_chinese_enabled: bool = True,
) -> tuple[str, list[AppliedCorrection], str | None]:
    final_text, corrections, warning = normalize_text(
        text=raw_text,
        hotword_map=hotword_map,
        punctuation_enabled=punctuation_enabled,
        spacing_enabled=spacing_enabled,
        simplified_chinese_enabled=simplified_chinese_enabled,
    )
    return final_text, corrections, warning
