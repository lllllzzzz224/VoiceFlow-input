from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.settings import settings


class HistoryStore:
    def __init__(self, history_path: str) -> None:
        self._lock = threading.Lock()
        self._path = Path(history_path)

    def set_path(self, history_path: str) -> None:
        with self._lock:
            self._path = Path(history_path)

    def get_path(self) -> str:
        with self._lock:
            return str(self._path)

    def list_items(self) -> list[dict[str, Any]]:
        with self._lock:
            return self._read_locked()

    def append(self, item: dict[str, Any]) -> None:
        with self._lock:
            items = self._read_locked()
            items.append(item)
            self._write_locked(items)

    def clear(self) -> int:
        with self._lock:
            items = self._read_locked()
            count = len(items)
            self._write_locked([])
            return count

    def _ensure_parent(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read_locked(self) -> list[dict[str, Any]]:
        self._ensure_parent()
        if not self._path.exists():
            return []
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
            return []
        except Exception:
            return []

    def _write_locked(self, items: list[dict[str, Any]]) -> None:
        self._ensure_parent()
        temp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temp_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self._path)


history_store = HistoryStore(settings.history_file_path)

