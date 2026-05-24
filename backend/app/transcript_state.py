from __future__ import annotations


def _trim_for_merge(text: str) -> str:
    return (text or "").strip().strip(" ,.;!?\u3002\uff01\uff1f\uff1b\uff0c")


class TranscriptState:
    def __init__(self) -> None:
        self._merged = ""

    def append_partial(self, segment_text: str) -> str:
        new_text = _trim_for_merge(segment_text)
        if not new_text:
            return self._merged

        if not self._merged:
            self._merged = new_text
            return self._merged

        tail_window = self._merged[-max(len(new_text) + 10, 40) :]
        if new_text in tail_window:
            return self._merged

        max_overlap = min(30, len(self._merged), len(new_text))
        overlap = 0
        for size in range(max_overlap, 0, -1):
            if self._merged.endswith(new_text[:size]):
                overlap = size
                break

        if overlap > 0:
            self._merged += new_text[overlap:]
        else:
            self._merged = f"{self._merged} {new_text}".strip()

        return self._merged

    def get_merged_text(self) -> str:
        return self._merged
