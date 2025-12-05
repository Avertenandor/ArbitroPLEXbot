"""
Примеры использования дашборда заработка.

Этот файл содержит готовые примеры кода для работы с сервисом
статистики заработка пользователей.
"""

from decimal import Decimal
from typing import Any

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.earnings_stats_service import EarningsStatsService
from bot.utils.formatters import format_usdt


# ============================================================================
# ПРИМЕР 1: Получить заработок за разные периоды
# ============================================================================

async def example_get_period_earnings(session: AsyncSession, user_id: int):
    """Получить заработок за разные периоды."""
    earnings_service = EarningsStatsService(session)

    # За сегодня
    today = await earnings_service.get_today_earnings(user_id)
    print(f"Заработок за сегодня: {format_usdt(today)} USDT")

    # За неделю
    week = await earnings_service.get_week_earnings(user_id)
    print(f"Заработок за неделю: {format_usdt(week)} USDT")

    # За месяц
    month = await earnings_service.get_month_earnings(user_id)
    print(f"Заработок за месяц: {format_usdt(month)} USDT")

    # За произвольный период (например, 14 дней)
    two_weeks = await earnings_service.get_period_earnings(user_id, period_days=14)
    print(f"Заработок за 14 дней: {format_usdt(two_weeks)} USDT")


# ============================================================================
# ПРИМЕР 2: Получить полную статистику заработка
# ============================================================================

async def example_get_full_stats(session: AsyncSession, user_id: int):
    """Получить полную статистику заработка."""
    earnings_service = EarningsStatsService(session)
    stats = await earnings_service.get_full_earnings_stats(user_id)

    if not stats:
        print("Статистика недоступна")
        return

    # Заработок по периодам
    print(f"Сегодня: {format_usdt(stats['today'])} USDT")
    print(f"За неделю: {format_usdt(stats['week'])} USDT")
    print(f"За месяц: {format_usdt(stats['month'])} USDT")

    # Балансы
    print(f"\nВсего заработано: {format_usdt(stats['total_earned'])} USDT")
    print(f"Ожидает вывода: {format_usdt(stats['pending_earnings'])} USDT")
    print(f"Доступно сейчас: {format_usdt(stats['available_balance'])} USDT")
    print(f"Уже выплачено: {format_usdt(stats['total_paid'])} USDT")

    # ROI прогресс
    print("\nROI прогресс:")
    for roi in stats['roi_progress']:
        level = roi['level']
        percent = roi['roi_percent']
        paid = format_usdt(roi['roi_paid'])
        cap = format_usdt(roi['roi_cap'])
        print(f"Level {level}: {percent:.1f}% ({paid}/{cap} USDT)")


# ============================================================================
# ПРИМЕР 3: Получить ROI прогресс
# ============================================================================

async def example_get_roi_progress(session: AsyncSession, user_id: int):
    """Получить ROI прогресс по всем уровням."""
    earnings_service = EarningsStatsService(session)
    roi_list = await earnings_service.get_roi_progress_all_levels(user_id)

    if not roi_list:
        print("Нет активных депозитов")
        return

    print("ROI прогресс по уровням:")
    for roi in roi_list:
        level = roi['level']
        deposit_id = roi['deposit_id']
        deposit_amount = format_usdt(roi['deposit_amount'])
        roi_percent = roi['roi_percent']
        roi_paid = format_usdt(roi['roi_paid'])
        roi_cap = format_usdt(roi['roi_cap'])
        roi_remaining = format_usdt(roi['roi_remaining'])
        is_completed = roi['is_completed']

        print(f"\nLevel {level} (Депозит #{deposit_id}):")
        print(f"  Сумма депозита: {deposit_amount} USDT")
        print(f"  Прогресс: {roi_percent:.1f}%")
        print(f"  Выплачено: {roi_paid} USDT")
        print(f"  Лимит: {roi_cap} USDT")
        print(f"  Осталось: {roi_remaining} USDT")
        print(f"  Завершён: {'Да' if is_completed else 'Нет'}")


# ============================================================================
# ПРИМЕР 4: Получить разбивку заработка по типам транзакций
# ============================================================================

async def example_get_breakdown(session: AsyncSession, user_id: int):
    """Получить разбивку заработка по типам транзакций."""
    earnings_service = EarningsStatsService(session)

    # За всё время
    print("За всё время:")
    all_time = await earnings_service.get_earnings_breakdown_by_type(user_id)
    print(f"  ROI: {format_usdt(all_time['deposit_reward'])} USDT")
    print(f"  Рефералы: {format_usdt(all_time['referral_reward'])} USDT")
    print(f"  Системные: {format_usdt(all_time['system_payout'])} USDT")

    # За последние 7 дней
    print("\nЗа последние 7 дней:")
    week = await earnings_service.get_earnings_breakdown_by_type(user_id, period_days=7)
    print(f"  ROI: {format_usdt(week['deposit_reward'])} USDT")
    print(f"  Рефералы: {format_usdt(week['referral_reward'])} USDT")
    print(f"  Системные: {format_usdt(week['system_payout'])} USDT")

    # За последние 30 дней
    print("\nЗа последние 30 дней:")
    month = await earnings_service.get_earnings_breakdown_by_type(user_id, period_days=30)
    print(f"  ROI: {format_usdt(month['deposit_reward'])} USDT")
    print(f"  Рефералы: {format_usdt(month['referral_reward'])} USDT")
    print(f"  Системные: {format_usdt(month['system_payout'])} USDT")


# ============================================================================
# ПРИМЕР 5: Создать кастомный обработчик для бота
# ============================================================================

router = Router()


@router.message(F.text == "💰 Моя статистика")
async def custom_earnings_handler(
    message: Message,
    session: AsyncSession,
    **data: Any
):
    """Кастомный обработчик статистики заработка."""
    user_id = message.from_user.id
    earnings_service = EarningsStatsService(session)

    # Получить данные
    stats = await earnings_service.get_full_earnings_stats(user_id)
    breakdown = await earnings_service.get_earnings_breakdown_by_type(
        user_id, period_days=7
    )

    if not stats:
        await message.answer("Статистика недоступна")
        return

    # Форматировать сообщение
    text = (
        f"📊 *Статистика за неделю*\n\n"
        f"Всего: {format_usdt(stats['week'])} USDT\n\n"
        f"Из них:\n"
        f"• ROI: {format_usdt(breakdown['deposit_reward'])} USDT\n"
        f"• Рефералы: {format_usdt(breakdown['referral_reward'])} USDT\n"
        f"• Системные: {format_usdt(breakdown['system_payout'])} USDT\n"
    )

    await message.answer(text, parse_mode="Markdown")


# ============================================================================
# ПРИМЕР 6: Добавить статистику в профиль
# ============================================================================

async def add_earnings_to_profile(
    message: Message,
    session: AsyncSession,
    user_id: int,
    existing_text: str
) -> str:
    """Добавить статистику заработка в профиль."""
    earnings_service = EarningsStatsService(session)

    # Получить статистику
    today = await earnings_service.get_today_earnings(user_id)
    week = await earnings_service.get_week_earnings(user_id)
    month = await earnings_service.get_month_earnings(user_id)

    # Добавить к существующему тексту
    earnings_text = (
        f"\n*💰 Заработок:*\n"
        f"📊 Сегодня: +{format_usdt(today)} USDT\n"
        f"📅 За неделю: +{format_usdt(week)} USDT\n"
        f"📆 За месяц: +{format_usdt(month)} USDT\n"
    )

    return existing_text + earnings_text


# ============================================================================
# ПРИМЕР 7: Отправить ежедневное уведомление о заработке
# ============================================================================

async def send_daily_earnings_notification(
    bot,
    session: AsyncSession,
    user_id: int,
    telegram_id: int
):
    """Отправить ежедневное уведомление о заработке."""
    earnings_service = EarningsStatsService(session)

    # Получить статистику
    today = await earnings_service.get_today_earnings(user_id)
    week = await earnings_service.get_week_earnings(user_id)

    # Отправить только если был заработок сегодня
    if today > 0:
        text = (
            f"🎉 *Отчёт за сегодня*\n\n"
            f"💰 Заработано сегодня: +{format_usdt(today)} USDT\n"
            f"📊 За неделю: +{format_usdt(week)} USDT\n\n"
            f"Отличная работа! Продолжайте в том же духе!"
        )

        await bot.send_message(
            telegram_id,
            text,
            parse_mode="Markdown"
        )


# ============================================================================
# ПРИМЕР 8: Форматировать прогресс-бар для ROI
# ============================================================================

def format_progress_bar(percent: float, width: int = 10) -> str:
    """
    Форматировать прогресс-бар для отображения ROI.

    Args:
        percent: Процент выполнения (0-100)
        width: Ширина прогресс-бара в символах

    Returns:
        Строка прогресс-бара с заполненными и пустыми блоками
    """
    filled = round((percent / 100) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


async def example_format_roi_with_progress(session: AsyncSession, user_id: int):
    """Показать ROI с прогресс-баром."""
    earnings_service = EarningsStatsService(session)
    roi_list = await earnings_service.get_roi_progress_all_levels(user_id)

    for roi in roi_list:
        level = roi['level']
        percent = roi['roi_percent']
        paid = format_usdt(roi['roi_paid'])
        cap = format_usdt(roi['roi_cap'])

        # Форматировать прогресс-бар
        progress_bar = format_progress_bar(percent)

        print(f"Level {level}: {progress_bar} {percent:.1f}%")
        print(f"└ {paid}/{cap} USDT\n")


# ============================================================================
# ПРИМЕР 9: Обработка ошибок
# ============================================================================

async def example_error_handling(session: AsyncSession, user_id: int):
    """Пример безопасной обработки ошибок."""
    earnings_service = EarningsStatsService(session)

    try:
        # Все методы сервиса безопасны и возвращают значения по умолчанию при ошибках
        stats = await earnings_service.get_full_earnings_stats(user_id)

        if not stats:
            print("Статистика недоступна (пустой словарь)")
            return

        # Безопасный доступ к полям с get()
        today = stats.get('today', Decimal('0'))
        roi_progress = stats.get('roi_progress', [])

        print(f"Заработок за сегодня: {format_usdt(today)} USDT")
        print(f"Активных депозитов: {len(roi_progress)}")

    except Exception as e:
        # Дополнительная обработка на всякий случай
        print(f"Ошибка: {e}")


# ============================================================================
# ПРИМЕР 10: Сравнение заработка за периоды
# ============================================================================

async def example_compare_periods(session: AsyncSession, user_id: int):
    """Сравнить заработок за разные периоды."""
    earnings_service = EarningsStatsService(session)

    # Получить заработок за разные периоды
    today = await earnings_service.get_today_earnings(user_id)
    week = await earnings_service.get_week_earnings(user_id)
    month = await earnings_service.get_month_earnings(user_id)

    # Рассчитать средние значения
    avg_per_day_week = week / 7 if week > 0 else Decimal('0')
    avg_per_day_month = month / 30 if month > 0 else Decimal('0')

    print("📊 Анализ заработка:")
    print(f"\nЗа сегодня: {format_usdt(today)} USDT")
    print(f"За неделю: {format_usdt(week)} USDT")
    print(f"За месяц: {format_usdt(month)} USDT")

    print(f"\nСредний заработок в день:")
    print(f"  По неделе: {format_usdt(avg_per_day_week)} USDT/день")
    print(f"  По месяцу: {format_usdt(avg_per_day_month)} USDT/день")

    # Сравнить с сегодняшним днём
    if avg_per_day_week > 0:
        if today > avg_per_day_week:
            diff = ((today / avg_per_day_week) - 1) * 100
            print(f"\n✅ Сегодня на {diff:.1f}% выше среднего!")
        else:
            diff = (1 - (today / avg_per_day_week)) * 100
            print(f"\n⚠️ Сегодня на {diff:.1f}% ниже среднего")


# ============================================================================
# ПРИМЕР 11: Создать отчёт для администратора
# ============================================================================

async def example_admin_report(session: AsyncSession, user_id: int):
    """Создать детальный отчёт для администратора."""
    earnings_service = EarningsStatsService(session)

    # Получить полную статистику
    stats = await earnings_service.get_full_earnings_stats(user_id)
    breakdown_all = await earnings_service.get_earnings_breakdown_by_type(user_id)
    breakdown_month = await earnings_service.get_earnings_breakdown_by_type(
        user_id, period_days=30
    )

    if not stats:
        return "Статистика недоступна"

    # Форматировать отчёт
    report = f"""
📊 ОТЧЁТ О ЗАРАБОТКЕ ПОЛЬЗОВАТЕЛЯ #{user_id}

👤 Пользователь: {stats.get('username', 'N/A')}

━━━━━━━━━━━━━━━━━━━━
💰 ЗАРАБОТОК ПО ПЕРИОДАМ
━━━━━━━━━━━━━━━━━━━━
Сегодня:    {format_usdt(stats['today'])} USDT
Неделя:     {format_usdt(stats['week'])} USDT
Месяц:      {format_usdt(stats['month'])} USDT

━━━━━━━━━━━━━━━━━━━━
💵 БАЛАНСЫ
━━━━━━━━━━━━━━━━━━━━
Всего заработано:  {format_usdt(stats['total_earned'])} USDT
Ожидает вывода:    {format_usdt(stats['pending_earnings'])} USDT
Доступно сейчас:   {format_usdt(stats['available_balance'])} USDT
Уже выплачено:     {format_usdt(stats['total_paid'])} USDT

━━━━━━━━━━━━━━━━━━━━
📊 РАЗБИВКА ПО ТИПАМ (ВСЁ ВРЕМЯ)
━━━━━━━━━━━━━━━━━━━━
ROI:         {format_usdt(breakdown_all['deposit_reward'])} USDT
Рефералы:    {format_usdt(breakdown_all['referral_reward'])} USDT
Системные:   {format_usdt(breakdown_all['system_payout'])} USDT

━━━━━━━━━━━━━━━━━━━━
📊 РАЗБИВКА ПО ТИПАМ (30 ДНЕЙ)
━━━━━━━━━━━━━━━━━━━━
ROI:         {format_usdt(breakdown_month['deposit_reward'])} USDT
Рефералы:    {format_usdt(breakdown_month['referral_reward'])} USDT
Системные:   {format_usdt(breakdown_month['system_payout'])} USDT

━━━━━━━━━━━━━━━━━━━━
📈 ROI ПРОГРЕСС
━━━━━━━━━━━━━━━━━━━━
"""

    # Добавить ROI по каждому уровню
    for roi in stats.get('roi_progress', []):
        level = roi['level']
        percent = roi['roi_percent']
        paid = format_usdt(roi['roi_paid'])
        cap = format_usdt(roi['roi_cap'])
        remaining = format_usdt(roi['roi_remaining'])

        progress_bar = format_progress_bar(percent)

        report += f"""
Level {level}: {progress_bar} {percent:.1f}%
  Депозит:    {format_usdt(roi['deposit_amount'])} USDT
  Выплачено:  {paid} USDT
  Лимит:      {cap} USDT
  Осталось:   {remaining} USDT
"""

    return report


# ============================================================================
# Запуск примеров (для тестирования)
# ============================================================================

async def run_all_examples(session: AsyncSession, user_id: int):
    """Запустить все примеры."""
    print("=" * 60)
    print("ПРИМЕР 1: Заработок за периоды")
    print("=" * 60)
    await example_get_period_earnings(session, user_id)

    print("\n" + "=" * 60)
    print("ПРИМЕР 2: Полная статистика")
    print("=" * 60)
    await example_get_full_stats(session, user_id)

    print("\n" + "=" * 60)
    print("ПРИМЕР 3: ROI прогресс")
    print("=" * 60)
    await example_get_roi_progress(session, user_id)

    print("\n" + "=" * 60)
    print("ПРИМЕР 4: Разбивка по типам")
    print("=" * 60)
    await example_get_breakdown(session, user_id)

    print("\n" + "=" * 60)
    print("ПРИМЕР 8: ROI с прогресс-баром")
    print("=" * 60)
    await example_format_roi_with_progress(session, user_id)

    print("\n" + "=" * 60)
    print("ПРИМЕР 10: Сравнение периодов")
    print("=" * 60)
    await example_compare_periods(session, user_id)

    print("\n" + "=" * 60)
    print("ПРИМЕР 11: Отчёт для администратора")
    print("=" * 60)
    report = await example_admin_report(session, user_id)
    print(report)


if __name__ == "__main__":
    print("Этот файл содержит примеры использования сервиса статистики заработка.")
    print("Импортируйте нужные функции в ваш код:")
    print()
    print("from EARNINGS_CODE_EXAMPLES import (")
    print("    example_get_period_earnings,")
    print("    example_get_full_stats,")
    print("    example_get_roi_progress,")
    print("    # ... и другие")
    print(")")
