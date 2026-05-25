from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.adapters.base import TranscriptionInput
from app.asr_service import get_asr_adapter
from app.postprocess import run_postprocess
from app.settings import settings


@dataclass(frozen=True)
class EvalSample:
    id: str
    audio_path: pathlib.Path
    expected_text: str
    hotwords: list[str]
    language: str = "zh"
    asr_mode: str = "fast"


def _normalize_for_metric(text: str) -> str:
    return "".join(str(text).split()).lower()


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (0 if left_char == right_char else 1)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def calculate_cer(expected_text: str, actual_text: str) -> float:
    expected = _normalize_for_metric(expected_text)
    actual = _normalize_for_metric(actual_text)
    if not expected and not actual:
        return 0.0
    if not expected:
        return 1.0
    distance = _levenshtein_distance(expected, actual)
    return round(distance / len(expected), 4)


def evaluate_hotwords(expected_hotwords: list[str], actual_text: str) -> dict[str, Any]:
    actual_normalized = actual_text.lower()
    missing = [word for word in expected_hotwords if word.lower() not in actual_normalized]
    total = len(expected_hotwords)
    hit = total - len(missing)
    hit_rate = round(hit / total, 4) if total else 1.0
    return {
        "hit": hit,
        "total": total,
        "hit_rate": hit_rate,
        "missing": missing,
    }


def load_manifest(manifest_path: str) -> list[EvalSample]:
    path = pathlib.Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    samples_payload = payload.get("samples", [])
    if not isinstance(samples_payload, list):
        raise ValueError("manifest field `samples` must be a list")

    samples: list[EvalSample] = []
    for index, item in enumerate(samples_payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"sample #{index} must be an object")
        sample_id = str(item.get("id") or f"sample_{index:03d}")
        raw_audio_path = item.get("audio_path")
        expected_text = str(item.get("expected_text") or "").strip()
        if not raw_audio_path:
            raise ValueError(f"{sample_id}: audio_path is required")
        if not expected_text:
            raise ValueError(f"{sample_id}: expected_text is required")

        audio_path = pathlib.Path(str(raw_audio_path))
        if not audio_path.is_absolute():
            audio_path = (path.parent / audio_path).resolve()
        if not audio_path.exists():
            raise FileNotFoundError(f"{sample_id}: audio file not found: {audio_path}")

        hotwords_payload = item.get("hotwords", [])
        if not isinstance(hotwords_payload, list):
            raise ValueError(f"{sample_id}: hotwords must be a list")
        hotwords = [str(word).strip() for word in hotwords_payload if str(word).strip()]

        samples.append(
            EvalSample(
                id=sample_id,
                audio_path=audio_path,
                expected_text=expected_text,
                hotwords=hotwords,
                language=str(item.get("language") or settings.default_language),
                asr_mode=str(item.get("asr_mode") or "fast"),
            )
        )
    return samples


async def evaluate_sample(sample: EvalSample) -> dict[str, Any]:
    audio_bytes = sample.audio_path.read_bytes()
    started = time.perf_counter()
    adapter_output = await get_asr_adapter().transcribe(
        TranscriptionInput(
            audio_bytes=audio_bytes,
            language=sample.language,
            hotwords=sample.hotwords,
            asr_mode=sample.asr_mode,
            asr_mode_provided=True,
        )
    )
    raw_text = adapter_output.transcription.raw_text
    final_text, corrections, warning = run_postprocess(
        raw_text=raw_text,
        hotword_map=settings.build_hotword_map_for_session(sample.hotwords),
        punctuation_enabled=settings.postprocess_punctuation_enabled,
        spacing_enabled=settings.postprocess_spacing_enabled,
        simplified_chinese_enabled=settings.postprocess_simplified_chinese_enabled,
    )
    latency_ms = max(int((time.perf_counter() - started) * 1000), 1)
    return {
        "id": sample.id,
        "success": True,
        "audio_path": str(sample.audio_path),
        "expected_text": sample.expected_text,
        "raw_text": raw_text,
        "final_text": final_text,
        "cer": calculate_cer(sample.expected_text, final_text),
        "hotwords": evaluate_hotwords(sample.hotwords, final_text),
        "latency_ms": latency_ms,
        "decode_ms": adapter_output.decode_ms,
        "asr_ms": adapter_output.asr_ms,
        "audio_duration_ms": adapter_output.audio_duration_ms,
        "engine": adapter_output.transcription.engine.value,
        "model": adapter_output.model,
        "asr_mode": adapter_output.asr_mode,
        "model_cached": adapter_output.model_cached,
        "postprocess_warning": warning,
        "applied_corrections": [item.model_dump() for item in corrections],
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(results)
    successes = [item for item in results if item.get("success") is True]
    success_count = len(successes)
    average_cer = round(sum(float(item.get("cer", 0.0)) for item in successes) / success_count, 4) if successes else 0.0
    average_latency_ms = (
        round(sum(int(item.get("latency_ms", 0)) for item in successes) / success_count)
        if successes
        else 0
    )
    hotword_hit = sum(int(item.get("hotwords", {}).get("hit", 0)) for item in successes)
    hotword_total = sum(int(item.get("hotwords", {}).get("total", 0)) for item in successes)
    hotword_hit_rate = round(hotword_hit / hotword_total, 4) if hotword_total else 1.0
    return {
        "count": count,
        "success_count": success_count,
        "failure_count": count - success_count,
        "average_cer": average_cer,
        "average_latency_ms": average_latency_ms,
        "hotword_hit_rate": hotword_hit_rate,
        "asr_cost_cents": 0,
    }


async def evaluate_manifest(manifest_path: str) -> dict[str, Any]:
    samples = load_manifest(manifest_path)
    results: list[dict[str, Any]] = []
    for sample in samples:
        try:
            results.append(await evaluate_sample(sample))
        except Exception as exc:
            results.append(
                {
                    "id": sample.id,
                    "success": False,
                    "audio_path": str(sample.audio_path),
                    "expected_text": sample.expected_text,
                    "error": str(exc),
                    "hotwords": evaluate_hotwords(sample.hotwords, ""),
                }
            )
    return {
        "summary": summarize_results(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local ASR quality with CER, hotword hits, and latency.")
    parser.add_argument("--manifest", default="eval_manifest.json", help="Path to evaluation manifest JSON.")
    parser.add_argument("--output", default="", help="Optional output JSON path.")
    args = parser.parse_args()

    report = asyncio.run(evaluate_manifest(args.manifest))
    report_text = json.dumps(report, ensure_ascii=False, indent=2)
    print(report_text)
    if args.output:
        pathlib.Path(args.output).write_text(report_text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
