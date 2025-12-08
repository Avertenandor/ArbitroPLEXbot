"""Knowledge Base for ARIA AI Assistant."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from loguru import logger

KB_PATH = Path("/app/data/knowledge_base.json")
KB_PATH_LOCAL = Path("data/knowledge_base.json")


def get_kb_path() -> Path:
    if KB_PATH.parent.exists():
        return KB_PATH
    KB_PATH_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    return KB_PATH_LOCAL


DEFAULT_KB: list[dict[str, Any]] = [
    {"id": 1, "category": "PLEX", "question": "Что такое PLEX?",
     "answer": "PLEX - токен на BSC для входа (10) и депозитов (10 за $1).",
     "clarification": "Это ключ для участия в платформе.",
     "added_by": "system", "verified_by_boss": True},
    {"id": 2, "category": "PLEX", "question": "Адрес контракта PLEX?",
     "answer": "0x2b83BE51c7c4a662f592090AD2041001a4525664 (BSC/BEP-20)",
     "clarification": "Только BSC! Другие сети = потеря токенов.",
     "added_by": "system", "verified_by_boss": True},
    {"id": 3, "category": "PLEX", "question": "Как добавить в Trust Wallet?",
     "answer": "Настройки > Добавить токен > Smart Chain > вставить адрес",
     "clarification": "Выбирай Smart Chain, не Ethereum!",
     "added_by": "system", "verified_by_boss": True},
    {"id": 4, "category": "PLEX", "question": "Как добавить в SafePal?",
     "answer": "Активы > + > BSC > Вручную > вставить адрес контракта",
     "clarification": "Название подтянется автоматически.",
     "added_by": "system", "verified_by_boss": True},
    {"id": 10, "category": "Депозиты", "question": "Как сделать депозит?",
     "answer": "Депозит > сумма > отправить USDT (TRC-20) на адрес",
     "clarification": "Минимум $10. Нужны PLEX. Только TRC-20!",
     "added_by": "system", "verified_by_boss": True},
    {"id": 11, "category": "Депозиты", "question": "Депозит не пришел?",
     "answer": "Проверь hash на tronscan.org, жди 15 мин, пиши в поддержку",
     "clarification": "Частая ошибка - ERC-20 вместо TRC-20.",
     "added_by": "system", "verified_by_boss": True},
    {"id": 20, "category": "Выводы", "question": "Как вывести?",
     "answer": "Вывод > сумма > адрес USDT TRC-20 > подтвердить",
     "clarification": "Минимум $10. Обработка до 24-48ч.",
     "added_by": "system", "verified_by_boss": True},
    {"id": 30, "category": "ROI", "question": "Как начисляется ROI?",
     "answer": "Автоматически каждый день на активные депозиты.",
     "clarification": "Ставки не разглашаются, смотри в кабинете.",
     "added_by": "system", "verified_by_boss": True},
]


class KnowledgeBase:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
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
        try:
            kb_path = get_kb_path()
            kb_path.parent.mkdir(parents=True, exist_ok=True)
            with open(kb_path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"KB save error: {e}")

    def get_next_id(self) -> int:
        return max((e.get("id", 0) for e in self.entries), default=0) + 1

    def add_entry(self, question: str, answer: str, category: str = "Общее",
                  clarification: str = "", added_by: str = "admin") -> dict:
        entry = {
            "id": self.get_next_id(), "category": category,
            "question": question, "answer": answer,
            "clarification": clarification, "added_by": added_by,
            "added_at": datetime.now(UTC).isoformat(),
            "verified_by_boss": False
        }
        self.entries.append(entry)
        self.save()
        return entry

    def update_entry(self, entry_id: int, **kwargs) -> dict | None:
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
        for entry in self.entries:
            if entry.get("id") == entry_id:
                entry["verified_by_boss"] = True
                self.save()
                return True
        return False

    def delete_entry(self, entry_id: int) -> bool:
        for i, e in enumerate(self.entries):
            if e.get("id") == entry_id:
                del self.entries[i]
                self.save()
                return True
        return False

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        return [e for e in self.entries if q in str(e).lower()]

    def get_categories(self) -> list[str]:
        return sorted(set(e.get("category", "") for e in self.entries))

    def get_unverified(self) -> list[dict]:
        return [e for e in self.entries if not e.get("verified_by_boss")]

    def format_for_ai(self) -> str:
        lines = ["=== БАЗА ЗНАНИЙ ===", "Источник: @VladarevInvestBrok", ""]
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


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
