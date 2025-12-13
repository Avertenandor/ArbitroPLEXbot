"""CRUD operations for Knowledge Base."""

from datetime import UTC, datetime
from typing import Any

from loguru import logger


class CRUDMixin:
    """Mixin for Create, Read, Update, Delete operations."""

    def __init__(self) -> None:
        """Initialize CRUD mixin."""
        self.entries: list[dict[str, Any]] = []

    def get_next_id(self) -> int:
        """Get the next available ID for a new entry.

        Returns:
            Next ID (max existing ID + 1, or 1 if no entries).
        """
        return max((e.get("id", 0) for e in self.entries), default=0) + 1

    def add_entry(
        self,
        question: str,
        answer: str,
        category: str = "Общее",
        clarification: str = "",
        added_by: str = "admin",
    ) -> dict:
        """Add a new entry to the knowledge base.

        Args:
            question: The question text
            answer: The answer text
            category: Category for organization (default: "Общее")
            clarification: Additional clarification text
            added_by: Username who added the entry

        Returns:
            The newly created entry dictionary
        """
        entry = {
            "id": self.get_next_id(),
            "category": category,
            "question": question,
            "answer": answer,
            "clarification": clarification,
            "added_by": added_by,
            "added_at": datetime.now(UTC).isoformat(),
            "verified_by_boss": False,
        }
        self.entries.append(entry)
        self.save()
        return entry

    def update_entry(self, entry_id: int, **kwargs) -> dict | None:
        """Update an existing entry.

        Args:
            entry_id: ID of the entry to update
            **kwargs: Fields to update (question, answer, category, etc.)

        Returns:
            Updated entry dict, or None if entry not found
        """
        for entry in self.entries:
            if entry.get("id") == entry_id:
                for k, v in kwargs.items():
                    if v is not None and k in entry:
                        entry[k] = v
                entry["verified_by_boss"] = False
                self.save()
                return entry
        return None

    def verify_entry(self, entry_id: int) -> bool:
        """Mark an entry as verified by boss.

        Args:
            entry_id: ID of the entry to verify

        Returns:
            True if entry was found and verified, False otherwise
        """
        for entry in self.entries:
            if entry.get("id") == entry_id:
                entry["verified_by_boss"] = True
                self.save()
                return True
        return False

    def delete_entry(self, entry_id: int) -> bool:
        """Delete an entry from the knowledge base.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if entry was found and deleted, False otherwise
        """
        for i, e in enumerate(self.entries):
            if e.get("id") == entry_id:
                del self.entries[i]
                self.save()
                return True
        return False

    def add_learned_entry(
        self,
        question: str,
        answer: str,
        category: str = "Из диалогов",
        source_user: str = "unknown",
        needs_verification: bool = True,
    ) -> dict:
        """Add entry learned from conversation with admin/boss.

        Args:
            question: The question text
            answer: The answer text
            category: Category (default: "Из диалогов")
            source_user: Username of the source
            needs_verification: Whether boss verification is needed

        Returns:
            The newly created entry dictionary
        """
        entry = {
            "id": self.get_next_id(),
            "category": category,
            "question": question,
            "answer": answer,
            "clarification": f"Извлечено из диалога с @{source_user}",
            "added_by": "ARIA",
            "added_at": datetime.now(UTC).isoformat(),
            "verified_by_boss": not needs_verification,
            "learned_from_dialog": True,
            "source_user": source_user,
        }
        self.entries.append(entry)
        self.save()
        logger.info(
            f"ARIA learned: {question[:50]}... from @{source_user}"
        )
        return entry

    def save(self) -> None:
        """Save method to be implemented by storage mixin."""
        raise NotImplementedError("save() must be implemented")
