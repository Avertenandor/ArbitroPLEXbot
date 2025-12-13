"""Storage operations for Knowledge Base."""

import json
from typing import Any

from loguru import logger

from .constants import get_kb_path
from .data import DEFAULT_KB


class StorageMixin:
    """Mixin for loading and saving knowledge base data."""

    def __init__(self) -> None:
        """Initialize storage mixin."""
        self.entries: list[dict[str, Any]] = []

    def load(self) -> None:
        """Load knowledge base from JSON file.

        Falls back to DEFAULT_KB if file doesn't exist or
        if loading fails.
        """
        kb_path = get_kb_path()
        try:
            if kb_path.exists():
                with open(kb_path, encoding="utf-8") as f:
                    self.entries = json.load(f)
            else:
                self.entries = DEFAULT_KB.copy()
                self.save()
        except Exception as e:
            logger.error(f"KB load error: {e}")
            self.entries = DEFAULT_KB.copy()

    def save(self) -> None:
        """Save knowledge base to JSON file.

        Creates parent directories if they don't exist.
        Logs errors but doesn't raise exceptions.
        """
        try:
            kb_path = get_kb_path()
            kb_path.parent.mkdir(parents=True, exist_ok=True)
            with open(kb_path, "w", encoding="utf-8") as f:
                json.dump(
                    self.entries, f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.error(f"KB save error: {e}")
