"""
AI Interview Service - allows ARIA to conduct interviews with admins.

This service manages active interviews where ARIA sends questions
to admins and collects their answers for the knowledge base.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from aiogram import Bot
from loguru import logger


@dataclass
class Interview:
    """Active interview session."""

    interviewer_id: int  # Admin who started the interview (e.g., Командир)
    target_admin_id: int  # Admin being interviewed
    target_admin_username: str
    topic: str  # Topic of the interview
    questions: list[str]  # List of questions to ask
    current_question_idx: int = 0
    answers: list[dict[str, str]] = field(default_factory=list)  # Q&A pairs
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"  # active, completed, cancelled


class AIInterviewService:
    """Service for ARIA to conduct interviews with admins."""

    # In-memory storage for active interviews
    # Key: target_admin_id, Value: Interview
    _active_interviews: dict[int, Interview] = {}

    # Timeout for waiting response (in minutes)
    RESPONSE_TIMEOUT_MINUTES = 30

    def __init__(self, bot: Bot):
        self.bot = bot

    @classmethod
    def get_active_interview(cls, target_admin_id: int) -> Interview | None:
        """Get active interview for a target admin."""
        interview = cls._active_interviews.get(target_admin_id)
        if interview and interview.status == "active":
            # Check timeout
            if datetime.utcnow() - interview.last_activity > timedelta(
                minutes=cls.RESPONSE_TIMEOUT_MINUTES
            ):
                interview.status = "cancelled"
                logger.info(f"Interview with {target_admin_id} timed out")
                return None
            return interview
        return None

    @classmethod
    def has_active_interview(cls, target_admin_id: int) -> bool:
        """Check if admin has an active interview."""
        return cls.get_active_interview(target_admin_id) is not None

    async def start_interview(
        self,
        interviewer_id: int,
        target_admin_id: int,
        target_admin_username: str,
        topic: str,
        questions: list[str],
    ) -> dict[str, Any]:
        """
        Start an interview with an admin.

        Args:
            interviewer_id: Who initiated (e.g., super_admin telegram_id)
            target_admin_id: Admin being interviewed (telegram_id)
            target_admin_username: Username for display
            topic: Topic/subject of the interview
            questions: List of questions to ask

        Returns:
            Result dict with status
        """
        if not questions:
            return {
                "success": False,
                "error": "Нет вопросов для интервью",
            }

        # Check if already has active interview
        if self.has_active_interview(target_admin_id):
            return {
                "success": False,
                "error": f"@{target_admin_username} уже участвует в интервью",
            }

        # Create interview
        interview = Interview(
            interviewer_id=interviewer_id,
            target_admin_id=target_admin_id,
            target_admin_username=target_admin_username,
            topic=topic,
            questions=questions,
        )

        # Store
        self._active_interviews[target_admin_id] = interview

        # Send first question
        await self._send_next_question(interview)

        logger.info(
            f"ARIA started interview with @{target_admin_username} "
            f"on topic '{topic}', {len(questions)} questions"
        )

        return {
            "success": True,
            "target": f"@{target_admin_username}",
            "topic": topic,
            "total_questions": len(questions),
            "message": f"Начато интервью с @{target_admin_username} по теме '{topic}'",
        }

    async def _send_next_question(self, interview: Interview) -> bool:
        """Send the next question to the admin."""
        if interview.current_question_idx >= len(interview.questions):
            return False

        question = interview.questions[interview.current_question_idx]
        question_num = interview.current_question_idx + 1
        total = len(interview.questions)

        message = (
            f"📋 **Интервью: {interview.topic}**\n"
            f"Вопрос {question_num}/{total}:\n\n"
            f"❓ {question}\n\n"
            f"_Ответьте на этот вопрос. Ваш ответ будет сохранён в базу знаний._"
        )

        try:
            await self.bot.send_message(
                interview.target_admin_id,
                message,
                parse_mode="Markdown",
            )
            interview.last_activity = datetime.utcnow()
            return True
        except Exception as e:
            logger.error(f"Failed to send interview question: {e}")
            return False

    async def process_answer(
        self,
        target_admin_id: int,
        answer_text: str,
    ) -> dict[str, Any]:
        """
        Process an answer from the interviewed admin.

        Args:
            target_admin_id: Who answered (telegram_id)
            answer_text: Their answer

        Returns:
            Result dict with next action info
        """
        interview = self.get_active_interview(target_admin_id)
        if not interview:
            return {
                "has_interview": False,
                "message": None,
            }

        # Save the answer
        question = interview.questions[interview.current_question_idx]
        interview.answers.append({
            "question": question,
            "answer": answer_text,
        })

        # Move to next question
        interview.current_question_idx += 1
        interview.last_activity = datetime.utcnow()

        # Check if more questions
        if interview.current_question_idx < len(interview.questions):
            # Send confirmation and next question
            await self.bot.send_message(
                target_admin_id,
                "✅ Ответ записан!\n\n"
                "Продолжаем интервью...",
                parse_mode="Markdown",
            )
            await asyncio.sleep(1)
            await self._send_next_question(interview)

            return {
                "has_interview": True,
                "completed": False,
                "answers_count": len(interview.answers),
                "remaining": len(interview.questions) - interview.current_question_idx,
            }
        else:
            # Interview completed
            interview.status = "completed"

            await self.bot.send_message(
                target_admin_id,
                f"🎉 **Интервью завершено!**\n\n"
                f"Спасибо за ответы! Всего записано {len(interview.answers)} ответов.\n"
                f"Информация будет добавлена в базу знаний.",
                parse_mode="Markdown",
            )

            # Notify interviewer
            await self._notify_interviewer_completed(interview)

            return {
                "has_interview": True,
                "completed": True,
                "answers": interview.answers,
                "topic": interview.topic,
                "target": interview.target_admin_username,
            }

    async def _notify_interviewer_completed(self, interview: Interview) -> None:
        """Notify the interviewer that interview is complete."""
        try:
            # Format answers for display
            answers_text = "\n\n".join([
                f"**Q:** {qa['question']}\n**A:** {qa['answer']}"
                for qa in interview.answers
            ])

            message = (
                f"📋 **Интервью завершено!**\n\n"
                f"👤 Респондент: @{interview.target_admin_username}\n"
                f"📝 Тема: {interview.topic}\n"
                f"📊 Записано ответов: {len(interview.answers)}\n\n"
                f"**Результаты:**\n\n{answers_text}\n\n"
                f"_Сохраняю в базу знаний..._"
            )

            # Telegram has 4096 char limit
            if len(message) > 4000:
                message = (
                    f"📋 **Интервью завершено!**\n\n"
                    f"👤 Респондент: @{interview.target_admin_username}\n"
                    f"📝 Тема: {interview.topic}\n"
                    f"📊 Записано ответов: {len(interview.answers)}\n\n"
                    f"_Ответы слишком длинные для показа. Сохраняю в базу знаний..._"
                )

            await self.bot.send_message(
                interview.interviewer_id,
                message,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to notify interviewer: {e}")

    def get_interview_answers(self, target_admin_id: int) -> list[dict[str, str]] | None:
        """Get answers from a completed interview."""
        interview = self._active_interviews.get(target_admin_id)
        if interview and interview.status == "completed":
            return interview.answers
        return None

    async def cancel_interview(self, target_admin_id: int) -> dict[str, Any]:
        """Cancel an active interview."""
        interview = self._active_interviews.get(target_admin_id)
        if not interview or interview.status != "active":
            return {
                "success": False,
                "error": "Нет активного интервью",
            }

        interview.status = "cancelled"

        await self.bot.send_message(
            target_admin_id,
            "❌ Интервью отменено.",
            parse_mode="Markdown",
        )

        logger.info(f"Interview with @{interview.target_admin_username} cancelled")

        return {
            "success": True,
            "message": f"Интервью с @{interview.target_admin_username} отменено",
        }

    def get_interview_status(self, target_admin_id: int) -> dict[str, Any] | None:
        """Get status of an interview."""
        interview = self._active_interviews.get(target_admin_id)
        if not interview:
            return None

        return {
            "target": f"@{interview.target_admin_username}",
            "topic": interview.topic,
            "status": interview.status,
            "total_questions": len(interview.questions),
            "answered": len(interview.answers),
            "remaining": len(interview.questions) - interview.current_question_idx,
            "started_at": interview.started_at.isoformat(),
            "last_activity": interview.last_activity.isoformat(),
        }

    @classmethod
    def get_all_active_interviews(cls) -> list[dict[str, Any]]:
        """Get all active interviews."""
        return [
            {
                "target_id": tid,
                "target": f"@{i.target_admin_username}",
                "topic": i.topic,
                "status": i.status,
                "answered": len(i.answers),
                "remaining": len(i.questions) - i.current_question_idx,
            }
            for tid, i in cls._active_interviews.items()
            if i.status == "active"
        ]


# Singleton instance
_interview_service: AIInterviewService | None = None


def get_interview_service(bot: Bot | None = None) -> AIInterviewService | None:
    """Get or create interview service singleton."""
    global _interview_service
    if _interview_service is None and bot is not None:
        _interview_service = AIInterviewService(bot)
    return _interview_service


def init_interview_service(bot: Bot) -> AIInterviewService:
    """Initialize interview service with bot."""
    global _interview_service
    _interview_service = AIInterviewService(bot)
    return _interview_service
