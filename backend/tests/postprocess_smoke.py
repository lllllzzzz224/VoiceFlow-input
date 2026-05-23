from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.postprocess import run_postprocess


def test_fixed_sentence() -> None:
    raw = "qi niu yun  Kodo  mcp"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map={"qi niu yun": "七牛云", "kodo": "Kodo", "mcp": "MCP"},
        punctuation_enabled=True,
        spacing_enabled=True,
    )
    assert warning is None
    assert final_text == "七牛云 Kodo MCP。"
    assert len(corrections) == 3


def test_failure_fallback() -> None:
    raw = "hello world"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=None,  # type: ignore[arg-type]
        punctuation_enabled=True,
        spacing_enabled=True,
    )
    assert final_text == raw
    assert corrections == []
    assert warning is not None and warning.startswith("POSTPROCESS_ERROR:")


def main() -> None:
    test_fixed_sentence()
    test_failure_fallback()
    print("postprocess_smoke: PASS")


if __name__ == "__main__":
    main()

