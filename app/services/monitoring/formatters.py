"""Formatters module for MonitoringService."""

from typing import Any


class FormatterService:
    """Service for formatting monitoring data for AI assistants."""

    @staticmethod
    def format_dashboard_for_ai(data: dict[str, Any]) -> str:
        """
        Format dashboard data as text for AI context.

        Args:
            data: Dashboard data dict

        Returns:
            Formatted text for AI prompt
        """
        lines = ["=== РЕАЛЬНЫЕ ДАННЫЕ ПЛАТФОРМЫ ==="]
        lines.append(f"Время: {data.get('generated_at', 'N/A')}")
        lines.append("")

        # Admin stats
        admin = data.get("admin", {})
        lines.append("📊 АДМИНИСТРАТОРЫ:")
        lines.append(f"  Всего админов: {admin.get('total_admins', 0)}")
        lines.append(
            f"  Активных за {admin.get('hours_period', 24)}ч: "
            f"{admin.get('active_admins_last_hours', 0)}"
        )
        lines.append(f"  Действий: {admin.get('total_actions', 0)}")

        # Admin list
        admins_list = admin.get("admins_list", [])
        if admins_list:
            lines.append("  Список админов:")
            for a in admins_list:
                status = "🚫" if a.get("blocked") else "✅"
                lines.append(
                    f"    {status} @{a.get('username')} "
                    f"({a.get('role')})"
                )

        # Top actions
        top_actions = admin.get("top_action_types", [])
        if top_actions:
            lines.append("  Топ действий:")
            for action in top_actions[:3]:
                lines.append(
                    f"    - {action['type']}: {action['count']}"
                )

        lines.append("")

        # User stats
        users = data.get("users", {})
        lines.append("👥 ПОЛЬЗОВАТЕЛИ:")
        lines.append(f"  Всего: {users.get('total_users', 0)}")
        lines.append(f"  Активных за 24ч: {users.get('active_24h', 0)}")
        lines.append(f"  Активных за 7д: {users.get('active_7d', 0)}")
        lines.append(f"  Новых сегодня: {users.get('new_today', 0)}")
        lines.append(
            f"  Верифицированных: {users.get('verified_users', 0)} "
            f"({users.get('verification_rate', 0)}%)"
        )
        lines.append("")

        # Financial stats
        fin = data.get("financial", {})
        lines.append("💰 ФИНАНСЫ:")
        lines.append(
            f"  Активных депозитов: "
            f"${fin.get('total_active_deposits', 0):,.2f} "
            f"({fin.get('total_deposits_count', 0)} шт)"
        )
        lines.append(
            f"  Новых за {fin.get('hours_period', 24)}ч: "
            f"${fin.get('recent_deposits', 0):,.2f} "
            f"({fin.get('recent_deposits_count', 0)} шт)"
        )
        lines.append(
            f"  Выводов за {fin.get('hours_period', 24)}ч: "
            f"${fin.get('recent_withdrawals', 0):,.2f} "
            f"({fin.get('recent_withdrawals_count', 0)} шт)"
        )
        lines.append(
            f"  Ожидают вывод: "
            f"{fin.get('pending_withdrawals_count', 0)} шт "
            f"(${fin.get('pending_withdrawals_amount', 0):,.2f})"
        )
        lines.append("")

        # Recent actions
        actions = data.get("recent_actions", [])
        if actions:
            lines.append("📋 ПОСЛЕДНИЕ ДЕЙСТВИЯ АДМИНОВ:")
            for action in actions[:5]:
                lines.append(
                    f"  [{action.get('time')}] "
                    f"@{action.get('admin')}: {action.get('type')}"
                )

        lines.append("")

        # Server metrics
        server = data.get("server", {})
        if server and not server.get("error"):
            lines.append("🖥️ СЕРВЕР:")
            lines.append(
                f"  CPU: {server.get('cpu_percent', 0)}% "
                f"({server.get('cpu_cores', 0)} ядер)"
            )
            lines.append(
                f"  RAM: {server.get('memory_used_gb', 0)}/"
                f"{server.get('memory_total_gb', 0)} GB "
                f"({server.get('memory_percent', 0)}%)"
            )
            lines.append(
                f"  Диск: {server.get('disk_used_gb', 0)}/"
                f"{server.get('disk_total_gb', 0)} GB "
                f"({server.get('disk_percent', 0)}%)"
            )
            lines.append(
                f"  Память бота: {server.get('bot_memory_mb', 0)} MB"
            )
            lines.append("")

        # Deposit details
        deposits = data.get("deposits", {})
        if deposits and not deposits.get("error"):
            lines.append("💵 ДЕПОЗИТЫ (детали):")
            lines.append(
                f"  Сегодня: {deposits.get('today_count', 0)} шт "
                f"(${deposits.get('today_amount', 0):,.2f})"
            )
            by_status = deposits.get("by_status", {})
            for status, info in by_status.items():
                lines.append(
                    f"  {status}: {info.get('count', 0)} шт "
                    f"(${info.get('amount', 0):,.2f})"
                )
            recent = deposits.get("recent", [])
            if recent:
                lines.append("  Последние депозиты:")
                for dep in recent[:5]:
                    lines.append(
                        f"    - ${dep.get('amount', 0):.2f} "
                        f"от @{dep.get('user')} ({dep.get('time')})"
                    )
            lines.append("")

        # Withdrawal details
        withdrawals = data.get("withdrawals", {})
        if withdrawals and not withdrawals.get("error"):
            pending_list = withdrawals.get("pending_list", [])
            if pending_list:
                lines.append("⏳ ОЖИДАЮЩИЕ ВЫВОДА:")
                for w in pending_list[:10]:
                    lines.append(
                        f"  - ${w.get('amount', 0):.2f} "
                        f"@{w.get('user')} "
                        f"(ждёт с {w.get('waiting_since')})"
                    )
                lines.append("")

        # Transaction summary
        txns = data.get("transactions", {})
        if txns and not txns.get("error"):
            lines.append("📊 ТРАНЗАКЦИИ ЗА 24Ч:")
            for tx_type, info in txns.items():
                lines.append(
                    f"  {tx_type}: {info.get('count', 0)} шт "
                    f"(${info.get('total', 0):,.2f})"
                )
            lines.append("")

        # User inquiries / support requests
        inquiries = data.get("inquiries", {})
        if inquiries and inquiries.get("available"):
            lines.append("📩 ОБРАЩЕНИЯ ПОЛЬЗОВАТЕЛЕЙ:")
            lines.append(
                f"  Всего обращений: {inquiries.get('total', 0)}"
            )
            lines.append(
                f"  🆕 Новых (ждут ответа): "
                f"{inquiries.get('new_count', 0)}"
            )
            lines.append(
                f"  🔄 В работе: {inquiries.get('in_progress_count', 0)}"
            )
            lines.append(
                f"  ✅ Закрыто: {inquiries.get('closed_count', 0)}"
            )

            recent_inquiries = inquiries.get("recent", [])
            if recent_inquiries:
                lines.append("  Последние обращения:")
                for inq in recent_inquiries[:10]:
                    status_emoji = {
                        "new": "🆕",
                        "in_progress": "🔄",
                        "closed": "✅",
                    }.get(inq.get("status"), "❓")
                    lines.append(
                        f"    {status_emoji} [{inq.get('created')}] "
                        f"@{inq.get('user')}: "
                        f"{inq.get('question', '')[:60]}..."
                    )
                    if inq.get("assigned_to") != "Не назначен":
                        lines.append(
                            f"       → Назначен: "
                            f"@{inq.get('assigned_to')}"
                        )
            lines.append("")

        # System health
        system = data.get("system", {})
        lines.append("✅ СТАТУС СИСТЕМЫ:")
        lines.append(f"  База данных: {system.get('database', 'N/A')}")
        lines.append(f"  Общий статус: {system.get('status', 'N/A')}")

        return "\n".join(lines)
