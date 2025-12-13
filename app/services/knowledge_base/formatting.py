"""Formatting operations for Knowledge Base output."""

from typing import Any


class FormattingMixin:
    """Mixin for formatting KB data for different purposes."""

    def __init__(self) -> None:
        """Initialize formatting mixin."""
        self.entries: list[dict[str, Any]] = []

    def get_categories(self) -> list[str]:
        """Get categories method to be implemented by search mixin."""
        raise NotImplementedError(
            "get_categories() must be implemented"
        )

    def format_for_ai(self) -> str:
        """Full KB format - USE SPARINGLY (high token cost!).

        Returns:
            Complete formatted knowledge base string
        """
        lines = [
            "=== БАЗА ЗНАНИЙ ===",
            "Источник: @VladarevInvestBrok",
            "",
        ]
        for cat in self.get_categories():
            lines.append(f"[{cat}]")
            for e in self.entries:
                if e.get("category") == cat:
                    v = "+" if e.get("verified_by_boss") else "?"
                    lines.append(f"{v} В: {e['question']}")
                    lines.append(f"  О: {e['answer']}")
                    if c := e.get("clarification"):
                        lines.append(f"  ! {c}")
            lines.append("")
        return "\n".join(lines)

    def format_compact(self) -> str:
        """Compact KB format - RECOMMENDED (saves 70% tokens!).

        Returns:
            Compact formatted knowledge base with critical entries
        """
        lines = ["=== КРАТКАЯ БАЗА ЗНАНИЙ ==="]
        # Only include verified critical entries
        critical_categories = [
            "PLEX токен",
            "Депозиты",
            "Сеть BSC",
            "Арбитраж",
        ]
        for cat in critical_categories:
            entries_in_cat = [
                e
                for e in self.entries
                if e.get("category") == cat
                and e.get("verified_by_boss")
            ]
            if entries_in_cat:
                lines.append(f"[{cat}]")
                for e in entries_in_cat[:3]:  # Max 3 per category
                    answer_preview = e["answer"][:150]
                    lines.append(
                        f"• {e['question']}: {answer_preview}..."
                    )
        lines.append("")
        lines.append("(Полная база доступна через search_knowledge_base)")
        return "\n".join(lines)
