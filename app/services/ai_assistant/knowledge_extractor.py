"""
Knowledge Extractor for AI Assistant.

Extracts knowledge from conversations and saves to knowledge base.
"""

import json
import re
from typing import Any

from loguru import logger

from app.config.operational_constants import AI_MAX_TOKENS_LONG
from app.config.security import is_super_admin


async def extract_knowledge(
    client: Any,
    model_haiku: str,
    conversation: list[dict],
    source_user: str,
    source_telegram_id: int | None = None,
) -> list[dict] | None:
    """
    Extract knowledge from conversation to add to knowledge base.

    ВАЖНО: Самообучение включено для ВСЕХ админов,
    которые общаются с Арьей в админском режиме.
    Доступ к этому режиму уже контролируется middleware и
    get_admin_or_deny(), поэтому дополнительный жёсткий
    whitelist (ARYA_TEACHERS) здесь больше не используется.

    Args:
        client: Anthropic client instance
        model_haiku: Haiku model name
        conversation: List of message dicts with role and content
        source_user: Username of the person in conversation
        source_telegram_id: Telegram ID for authorization check

    Returns:
        List of extracted Q&A pairs or None
    """
    if not client:
        return None

    try:
        # Определяем роль учителя для промпта
        teacher_role = (
            "КОМАНДИРОМ"
            if source_telegram_id and is_super_admin(source_telegram_id)
            else "АДМИНИСТРАТОРОМ"
        )

        extraction_prompt = f"""
Проанализируй диалог между {teacher_role} ({source_user}) \
платформы ArbitroPLEX и AI-ассистентом ARIA.

ТВОЯ ЗАДАЧА: Извлечь ЛЮБЫЕ ПОЛЕЗНЫЕ ЗНАНИЯ, ФАКТЫ и \
ИНСТРУКЦИИ из слов Командира.

ЧТО ИЗВЛЕКАТЬ (Приоритет):
1. ФАКТЫ О ПРОЕКТАХ: Любая информация о новых \
проектах, кроликах, NFT, FreeTube, PLEX и т.д.
2. БИЗНЕС-МОДЕЛИ: Как работают инвестиции, откуда \
доход, механика начислений.
3. ИНСТРУКЦИИ: Как общаться, что отвечать, стиль \
поведения.
4. ПРАВИЛА: Запреты, рекомендации, маркетинговые \
установки.

ЕСЛИ КОМАНДИР РАССКАЗЫВАЕТ О НОВОМ ПРОЕКТЕ \
(например, про кроликов):
- Сформулируй вопросы так, как их задал бы инвестор \
(Как это работает? Откуда доход? В чем суть?).
- В ответе сохрани ВСЕ ключевые детали (цифры, \
механика, преимущества).

НЕ ИЗВЛЕКАЙ:
- Технические команды (типа /start)
- Сообщения об ошибках
- Пустую болтовню ("привет", "как дела")

ВАЖНО:
- Если Командир делится информацией - это ЗНАНИЕ! \
Сохраняй его!
- Ответы должны быть информативными, но без воды.

Формат ответа (ТОЛЬКО JSON массив):
[
  {{
    "question": "Вопрос (например: Как работает модель \
кроликов?)",
    "answer": "Ответ (суть механики, факты)",
    "category": "Экосистема / NFT / Правила / и т.д."
  }}
]

ВСЕГДА возвращай записи, если есть хоть какая-то \
полезная информация!
Если совсем ничего полезного нет, ответь: []
"""

        messages = [
            {"role": "user", "content": extraction_prompt},
            {
                "role": "assistant",
                "content": "Понял, анализирую диалог...",
            },
            {
                "role": "user",
                "content": (
                    "Диалог:\n"
                    + "\n".join(
                        f"{m['role']}: {m['content']}"
                        for m in conversation[-20:]
                    )
                ),
            },
        ]

        # Use prompt caching for system prompt
        # (saves 90% on repeated calls)
        system_prompt = (
            "Ты помощник для извлечения знаний. "
            "Отвечай ТОЛЬКО валидным JSON массивом. "
            "Ответы должны быть КРАТКИМИ."
        )
        system_with_cache = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        response = client.messages.create(
            model=model_haiku,  # Use Haiku for extraction (12x cheaper)
            max_tokens=AI_MAX_TOKENS_LONG,
            system=system_with_cache,
            messages=messages,
        )

        if response.content and len(response.content) > 0:
            first_block = response.content[0]
            if not hasattr(first_block, "text") or not first_block.text:
                return None
            text = first_block.text.strip()

            # Try to extract JSON array from response
            # Sometimes Claude adds extra text before/after JSON
            # Non-greedy to capture only first JSON array
            json_match = re.search(r"\[[\s\S]*?\]", text)
            if json_match:
                json_text = json_match.group(0)
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError as je:
                    logger.warning(
                        f"JSON parse error in extracted text: {je}"
                    )

            # Fallback: try direct parse if starts with [
            if text.startswith("["):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass

            logger.debug(f"Could not extract JSON from: {text[:200]}")

    except Exception as e:
        logger.error(f"Knowledge extraction error: {e}")

    return None


async def save_learned_knowledge(
    qa_pairs: list[dict],
    source_user: str,
) -> int:
    """
    Save extracted knowledge to knowledge base.

    Args:
        qa_pairs: List of Q&A dictionaries with question, answer, category
        source_user: Username of the source

    Returns:
        Number of successfully saved entries
    """
    # Validate input
    if not qa_pairs:
        logger.debug(
            "save_learned_knowledge: empty qa_pairs, nothing to save"
        )
        return 0

    if not isinstance(qa_pairs, list):
        logger.warning(
            f"save_learned_knowledge: qa_pairs is not a list: "
            f"{type(qa_pairs)}"
        )
        return 0

    try:
        from app.services.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        saved = 0

        for qa in qa_pairs:
            # Validate each entry
            if not isinstance(qa, dict):
                logger.warning(
                    f"save_learned_knowledge: skipping non-dict entry: "
                    f"{type(qa)}"
                )
                continue

            question = (
                qa.get("question", "").strip() if qa.get("question") else ""
            )
            answer = (
                qa.get("answer", "").strip() if qa.get("answer") else ""
            )

            if not question or not answer:
                logger.debug(
                    f"save_learned_knowledge: skipping empty Q&A: "
                    f"q={bool(question)}, a={bool(answer)}"
                )
                continue

            # Limit entry size to prevent bloat
            if len(question) > 500:
                question = question[:500] + "..."
            if len(answer) > 2000:
                answer = answer[:2000] + "..."

            try:
                kb.add_learned_entry(
                    question=question,
                    answer=answer,
                    category=qa.get("category", "Из диалогов"),
                    source_user=source_user,
                    needs_verification=True,
                )
                saved += 1
            except Exception as entry_error:
                logger.error(
                    f"save_learned_knowledge: failed to save entry: "
                    f"{entry_error}"
                )
                continue

        logger.info(
            f"save_learned_knowledge: saved {saved}/{len(qa_pairs)} "
            f"entries from {source_user}"
        )
        return saved

    except ImportError as e:
        logger.error(
            f"save_learned_knowledge: knowledge_base import failed: {e}"
        )
        return 0
    except Exception as e:
        logger.error(f"save_learned_knowledge: unexpected error: {e}")
        return 0
