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
    # === ОСНОВАТЕЛЬ И КОМАНДА ===
    {"id": 1, "category": "Основатель",
     "question": "Кто создатель ArbitroPLEX и монеты PLEX?",
     "answer": (
         "Александр Владарев (@VladarevInvestBrok) — создатель экосистемы "
         "монеты PLEX, проектировщик, программист, аналитик. Создал несколько "
         "десятков серьёзных криптопродуктов и несколько видов фиатного бизнеса."
     ),
     "clarification": (
         "Александр известен нетривиальными криптопродуктами: арбитражные "
         "роботы, MEV-роботы, линейка торговых роботов. Также работает над "
         "собственной DEX-биржей."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 2, "category": "Основатель",
     "question": "Что такое FreeTube?",
     "answer": (
         "FreeTube — собственный блокчейн Александра Владарева, который сейчас "
         "разрабатывается и тестируется. Он альфа-совместим с Binance Smart Chain."
     ),
     "clarification": "Это перспективный проект экосистемы PLEX.",
     "added_by": "system", "verified_by_boss": True},

    # === ЭКОСИСТЕМА PLEX ===
    {"id": 10, "category": "Экосистема PLEX",
     "question": "Что такое экосистема Монеты PLEX?",
     "answer": (
         "Экосистема построена на циркуляции утилити-токена PLEX. "
         "Выпущено немногим более 12 миллионов токенов. Мощная ежедневная "
         "циркуляция вызывает системный подъём курса."
     ),
     "clarification": (
         "Часть PLEX, которые приносят пользователи, система продаёт для "
         "поддержания резервов USDT и PLEX для бонусов, выплат и наград."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 11, "category": "Экосистема PLEX",
     "question": "Какие ещё проекты используют PLEX?",
     "answer": (
         "Кроме ArbitroPLEX существует несколько партнёрских проектов, "
         "в которых работает утилити-токен PLEX."
     ),
     "clarification": "Подробности о партнёрских проектах у @VladarevInvestBrok.",
     "added_by": "system", "verified_by_boss": True},

    # === АТОМАРНЫЙ АРБИТРАЖ ===
    {"id": 20, "category": "Арбитраж",
     "question": "Как работает атомарный арбитраж?",
     "answer": (
         "Бот приносит 30-70% прибыли через атомарный арбитраж. "
         "У каждой монеты есть пулы ликвидности V2 и V3 на PancakeSwap с разной "
         "комиссией. После каждой сделки образуется арбитражная разница."
     ),
     "clarification": (
         "Арбитробот с закрытого защищённого сервера в рамках ОДНОЙ транзакции "
         "покупает в одном пуле, продаёт в другом и забирает разницу."
     ),
     "added_by": "system", "verified_by_boss": True},

    {"id": 21, "category": "Арбитраж",
     "question": "Почему нужен PLEX для арбитража?",
     "answer": (
         "Для доступа к боту и чтобы деньги зарабатывали на арбитраже, "
         "нужна Монета PLEX: 10 монет за вход + 10 монет на каждый $1 депозита."
     ),
     "clarification": (
         "Это создаёт постоянную циркуляцию монеты и поддерживает экономику."
     ),
     "added_by": "system", "verified_by_boss": True},

    # === ТОКЕН PLEX ===
    {"id": 30, "category": "PLEX токен",
     "question": "Что такое PLEX токен?",
     "answer": (
         "PLEX — утилити-токен на BNB Smart Chain (BEP-20). "
         "Всего выпущено ~12 млн токенов. Нужен для входа (10 PLEX) "
         "и для депозитов (10 PLEX за каждый $1)."
     ),
     "clarification": "Это ключ для участия в экосистеме ArbitroPLEX.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 31, "category": "PLEX токен",
     "question": "Адрес контракта PLEX?",
     "answer": "0x2b83BE51c7c4a662f592090AD2041001a4525664 (BSC/BEP-20)",
     "clarification": "ТОЛЬКО сеть BSC! Другие сети = потеря токенов!",
     "added_by": "system", "verified_by_boss": True},

    {"id": 32, "category": "PLEX токен",
     "question": "Как добавить PLEX в Trust Wallet?",
     "answer": (
         "1. Настройки > Добавить токен\n"
         "2. Сеть: Smart Chain (BNB)\n"
         "3. Вставить адрес: 0x2b83BE51c7c4a662f592090AD2041001a4525664\n"
         "4. Сохранить"
     ),
     "clarification": "Выбирай Smart Chain, НЕ Ethereum!",
     "added_by": "system", "verified_by_boss": True},

    {"id": 33, "category": "PLEX токен",
     "question": "Как добавить PLEX в SafePal?",
     "answer": (
         "Активы > + > BSC > Вручную > вставить адрес контракта"
     ),
     "clarification": "Название и символ подтянутся автоматически.",
     "added_by": "system", "verified_by_boss": True},

    # === ДЕПОЗИТЫ ===
    {"id": 40, "category": "Депозиты",
     "question": "Как сделать депозит?",
     "answer": (
         "1. Убедись что есть PLEX (10 за вход + 10 за каждый $1)\n"
         "2. Депозит > выбери сумму\n"
         "3. Отправь USDT на указанный адрес (сеть BSC/BEP-20)\n"
         "4. Жди подтверждения (1-5 мин)"
     ),
     "clarification": "Минимум $10. ТОЛЬКО сеть BSC (BNB Smart Chain, BEP-20)!",
     "added_by": "system", "verified_by_boss": True},

    {"id": 41, "category": "Депозиты",
     "question": "Депозит не пришёл, что делать?",
     "answer": (
         "1. Проверь hash на bscscan.com\n"
         "2. Убедись что отправил по сети BSC (BEP-20)\n"
         "3. Подожди 15 минут\n"
         "4. Пиши в поддержку с hash"
     ),
     "clarification": "Частая ошибка: ERC-20 или TRC-20 вместо BSC = потеря средств!",
     "added_by": "system", "verified_by_boss": True},

    # === ВЫВОДЫ ===
    {"id": 50, "category": "Выводы",
     "question": "Как вывести деньги?",
     "answer": (
         "Вывод > сумма > адрес USDT (сеть BSC/BEP-20) > подтвердить. "
         "Минимум $10. Обработка до 24-48ч."
     ),
     "clarification": "ВАЖНО: Указывай адрес ТОЛЬКО в сети BSC (BNB Smart Chain)! Выводы обрабатываются вручную.",
     "added_by": "system", "verified_by_boss": True},

    # === ROI ===
    {"id": 60, "category": "ROI и доход",
     "question": "Как начисляется ROI?",
     "answer": (
         "ROI начисляется автоматически каждый день на активные депозиты. "
         "Прибыль падает на ваш баланс, НЕ на депозит. "
         "Доходность 30-70% зависит от рыночных условий арбитража."
     ),
     "clarification": "Прибыль можно вывести или сделать новый депозит.",
     "added_by": "system", "verified_by_boss": True},

    {"id": 61, "category": "ROI и доход",
     "question": "Есть ли реинвест?",
     "answer": (
         "НЕТ, функции реинвеста не существует! "
         "Каждый депозит — это отдельный уровень с отдельными условиями. "
         "Прибыль начисляется на баланс, а не добавляется к депозиту."
     ),
     "clarification": (
         "Чтобы увеличить рабочую сумму — нужно сделать НОВЫЙ депозит. "
         "Для нового депозита нужны новые PLEX токены."
     ),
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

    def add_learned_entry(
        self,
        question: str,
        answer: str,
        category: str = "Из диалогов",
        source_user: str = "unknown",
        needs_verification: bool = True,
    ) -> dict:
        """Add entry learned from conversation with admin/boss."""
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
        logger.info(f"ARIA learned: {question[:50]}... from @{source_user}")
        return entry

    def get_learned_entries(self) -> list[dict]:
        """Get entries that were learned from dialogs."""
        return [e for e in self.entries if e.get("learned_from_dialog")]

    def get_pending_verification(self) -> list[dict]:
        """Get entries pending boss verification."""
        return [
            e for e in self.entries
            if e.get("learned_from_dialog") and not e.get("verified_by_boss")
        ]


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
