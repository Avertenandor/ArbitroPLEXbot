"""Search and filtering operations for Knowledge Base."""

from typing import Any


class SearchMixin:
    """Mixin for search and filtering operations."""

    def __init__(self) -> None:
        """Initialize search mixin."""
        self.entries: list[dict[str, Any]] = []

    def search(self, query: str) -> list[dict]:
        """Basic search across all entry fields.

        Args:
            query: Search query string (case-insensitive)

        Returns:
            List of entries matching the query
        """
        q = query.lower()
        return [e for e in self.entries if q in str(e).lower()]

    def get_categories(self) -> list[str]:
        """Get all unique categories in the knowledge base.

        Returns:
            Sorted list of unique category names
        """
        return sorted(set(e.get("category", "") for e in self.entries))

    def get_unverified(self) -> list[dict]:
        """Get all entries not verified by boss.

        Returns:
            List of unverified entries
        """
        return [e for e in self.entries if not e.get("verified_by_boss")]

    def get_learned_entries(self) -> list[dict]:
        """Get entries that were learned from dialogs.

        Returns:
            List of entries with learned_from_dialog flag
        """
        return [e for e in self.entries if e.get("learned_from_dialog")]

    def get_entries_by_user(self, username: str) -> list[dict]:
        """Get entries added/learned from a specific user.

        Args:
            username: Username to search for (with or without @)

        Returns:
            List of entries associated with the user
        """
        username_lower = username.lower().replace("@", "")
        return [
            e
            for e in self.entries
            if username_lower in str(e.get("source_user", "")).lower()
            or username_lower in str(e.get("added_by", "")).lower()
            or username_lower
            in str(e.get("clarification", "")).lower()
        ]

    def get_pending_verification(self) -> list[dict]:
        """Get entries pending boss verification.

        Returns:
            List of learned entries not yet verified
        """
        return [
            e
            for e in self.entries
            if e.get("learned_from_dialog")
            and not e.get("verified_by_boss")
        ]

    def search_relevant(self, query: str, limit: int = 5) -> str:
        """Search KB and return only relevant entries (saves tokens!).

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            Formatted string with relevant entries
        """
        query_lower = query.lower()
        scored = []

        for e in self.entries:
            score = 0
            text = (
                f"{e.get('question', '')} {e.get('answer', '')} "
                f"{e.get('category', '')}"
            ).lower()

            # Score by keyword matches
            for word in query_lower.split():
                if len(word) > 2 and word in text:
                    score += 1

            if score > 0:
                scored.append((score, e))

        # Sort by score, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        top_entries = [e for _, e in scored[:limit]]

        if not top_entries:
            return ""

        lines = [
            f"=== РЕЛЕВАНТНЫЕ ЗНАНИЯ ({len(top_entries)} записей) ==="
        ]
        for e in top_entries:
            lines.append(f"В: {e['question']}")
            lines.append(f"О: {e['answer']}")
            if c := e.get("clarification"):
                lines.append(f"! {c}")
            lines.append("")

        return "\n".join(lines)
