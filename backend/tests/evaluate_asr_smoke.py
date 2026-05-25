from __future__ import annotations

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools.evaluate_asr import (
    calculate_cer,
    evaluate_hotwords,
    load_manifest,
    summarize_results,
)


def main() -> None:
    assert calculate_cer("VoiceFlow Input", "VoiceFlow Input") == 0.0
    assert calculate_cer("七牛云 Kodo", "七牛云 Kodo 对象存储") > 0.0
    assert calculate_cer("", "anything") == 1.0
    assert calculate_cer("", "") == 0.0

    hotword_result = evaluate_hotwords(
        expected_hotwords=["FastAPI", "WebSocket", "七牛云"],
        actual_text="VoiceFlow Input 使用 FastAPI 和 WebSocket 连接七牛云 Kodo。",
    )
    assert hotword_result["total"] == 3
    assert hotword_result["hit"] == 3
    assert hotword_result["missing"] == []

    with tempfile.TemporaryDirectory() as temp_dir:
        manifest_path = pathlib.Path(temp_dir) / "eval_manifest.json"
        audio_path = pathlib.Path(temp_dir) / "sample.webm"
        audio_path.write_bytes(b"fake-audio")
        manifest_path.write_text(
            json.dumps(
                {
                    "samples": [
                        {
                            "id": "sample_001",
                            "audio_path": str(audio_path),
                            "expected_text": "VoiceFlow Input 使用 FastAPI。",
                            "hotwords": ["VoiceFlow Input", "FastAPI"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        samples = load_manifest(str(manifest_path))
        assert len(samples) == 1
        assert samples[0].id == "sample_001"
        assert samples[0].audio_path == audio_path
        assert samples[0].expected_text == "VoiceFlow Input 使用 FastAPI。"

    summary = summarize_results(
        [
            {
                "cer": 0.1,
                "latency_ms": 1000,
                "hotwords": {"hit": 1, "total": 2, "missing": ["Kodo"]},
                "success": True,
            },
            {
                "cer": 0.2,
                "latency_ms": 1500,
                "hotwords": {"hit": 2, "total": 2, "missing": []},
                "success": True,
            },
        ]
    )
    assert summary["count"] == 2
    assert summary["success_count"] == 2
    assert summary["average_cer"] == 0.15
    assert summary["average_latency_ms"] == 1250
    assert summary["hotword_hit_rate"] == 0.75

    print("evaluate_asr_smoke: PASS")


if __name__ == "__main__":
    main()
