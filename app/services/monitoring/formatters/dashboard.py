"""
Dashboard formatter for monitoring service.

This module provides formatting utilities for dashboard data to be consumed by AI assistants.
"""

from typing import Any


class DashboardFormatter:
    """Formats dashboard data as text for AI context."""

    @staticmethod
    def format(data: dict[str, Any]) -> str:
        """
        Format dashboard data as text for AI context.

        Args:
            data: Dashboard data dict

        Returns:
            Formatted text for AI prompt
        """
        lines = []

        # Header
        lines.extend(DashboardFormatter._format_header(data.get('generated_at', 'N/A')))

        # Admin section
        admin = data.get("admin", {})
        lines.extend(DashboardFormatter._format_admin_section(admin))

        # Users section
        users = data.get("users", {})
        lines.extend(DashboardFormatter._format_users_section(users))

        # Financial section
        fin = data.get("financial", {})
        lines.extend(DashboardFormatter._format_financial_section(fin))

        # Recent actions
        actions = data.get("recent_actions", [])
        lines.extend(DashboardFormatter._format_recent_actions(actions))

        # Server metrics
        server = data.get("server", {})
        lines.extend(DashboardFormatter._format_server_section(server))

        # Deposit details
        deposits = data.get("deposits", {})
        lines.extend(DashboardFormatter._format_deposits_section(deposits))

        # Withdrawal details
        withdrawals = data.get("withdrawals", {})
        lines.extend(DashboardFormatter._format_withdrawals_section(withdrawals))

        # Transaction summary
        txns = data.get("transactions", {})
        lines.extend(DashboardFormatter._format_transactions_section(txns))

        # User inquiries / support requests
        inquiries = data.get("inquiries", {})
        lines.extend(DashboardFormatter._format_inquiries_section(inquiries))

        # System health
        system = data.get("system", {})
        lines.extend(DashboardFormatter._format_system_section(system))

        return "\n".join(lines)

    @staticmethod
    def _format_header(generated_at: str) -> list[str]:
        """
        Format dashboard header.

        Args:
            generated_at: Timestamp string

        Returns:
            List of formatted header lines
        """
        lines = ["=== РЕАЛЬНЫЕ ДАННЫЕ ПЛАТФОРМЫ ==="]
        lines.append(f"Время: {generated_at}")
        lines.append("")
        return lines

    @staticmethod
    def _format_admin_section(admin_data: dict) -> list[str]:
        """
        Format admin statistics section.

        Args:
            admin_data: Admin data dict

        Returns:
            List of formatted admin section lines
        """
        lines = []
        lines.append("📊 АДМИНИСТРАТОРЫ:")
        lines.append(f"  Всего админов: {admin_data.get('total_admins', 0)}")
        lines.append(f"  Активных за {admin_data.get('hours_period', 24)}ч: {admin_data.get('active_admins_last_hours', 0)}")
        lines.append(f"  Действий: {admin_data.get('total_actions', 0)}")

        # Admin list
        admins_list = admin_data.get("admins_list", [])
        if admins_list:
            lines.append("  Список админов:")
            for a in admins_list:
                status = "🚫" if a.get("blocked") else "✅"
                lines.append(f"    {status} @{a.get('username')} ({a.get('role')})")

        # Top actions
        top_actions = admin_data.get("top_action_types", [])
        if top_actions:
            lines.append("  Топ действий:")
            for action in top_actions[:3]:
                lines.append(f"    - {action['type']}: {action['count']}")

        lines.append("")
        return lines

    @staticmethod
    def _format_users_section(users_data: dict) -> list[str]:
        """
        Format users statistics section.

        Args:
            users_data: Users data dict

        Returns:
            List of formatted users section lines
        """
        lines = []
        lines.append("👥 ПОЛЬЗОВАТЕЛИ:")
        lines.append(f"  Всего: {users_data.get('total_users', 0)}")
        lines.append(f"  Активных за 24ч: {users_data.get('active_24h', 0)}")
        lines.append(f"  Активных за 7д: {users_data.get('active_7d', 0)}")
        lines.append(f"  Новых сегодня: {users_data.get('new_today', 0)}")
        lines.append(f"  Верифицированных: {users_data.get('verified_users', 0)} ({users_data.get('verification_rate', 0)}%)")
        lines.append("")
        return lines

    @staticmethod
    def _format_financial_section(fin_data: dict) -> list[str]:
        """
        Format financial statistics section.

        Args:
            fin_data: Financial data dict

        Returns:
            List of formatted financial section lines
        """
        lines = []
        lines.append("💰 ФИНАНСЫ:")
        lines.append(
            f"  Активных депозитов: ${fin_data.get('total_active_deposits', 0):,.2f} "
            f"({fin_data.get('total_deposits_count', 0)} шт)"
        )
        lines.append(
            f"  Новых за {fin_data.get('hours_period', 24)}ч: "
            f"${fin_data.get('recent_deposits', 0):,.2f} "
            f"({fin_data.get('recent_deposits_count', 0)} шт)"
        )
        lines.append(
            f"  Выводов за {fin_data.get('hours_period', 24)}ч: "
            f"${fin_data.get('recent_withdrawals', 0):,.2f} "
            f"({fin_data.get('recent_withdrawals_count', 0)} шт)"
        )
        lines.append(
            f"  Ожидают вывод: {fin_data.get('pending_withdrawals_count', 0)} шт "
            f"(${fin_data.get('pending_withdrawals_amount', 0):,.2f})"
        )
        lines.append("")
        return lines

    @staticmethod
    def _format_recent_actions(actions: list) -> list[str]:
        """
        Format recent admin actions section.

        Args:
            actions: List of recent actions

        Returns:
            List of formatted recent actions lines
        """
        lines = []
        if actions:
            lines.append("📋 ПОСЛЕДНИЕ ДЕЙСТВИЯ АДМИНОВ:")
            for action in actions[:5]:
                lines.append(f"  [{action.get('time')}] @{action.get('admin')}: {action.get('type')}")

        lines.append("")
        return lines

    @staticmethod
    def _format_server_section(server_data: dict) -> list[str]:
        """
        Format server metrics section.

        Args:
            server_data: Server data dict

        Returns:
            List of formatted server section lines
        """
        lines = []
        if server_data and not server_data.get("error"):
            lines.append("🖥️ СЕРВЕР:")
            lines.append(f"  CPU: {server_data.get('cpu_percent', 0)}% ({server_data.get('cpu_cores', 0)} ядер)")
            lines.append(
                f"  RAM: {server_data.get('memory_used_gb', 0)}/"
                f"{server_data.get('memory_total_gb', 0)} GB "
                f"({server_data.get('memory_percent', 0)}%)"
            )
            lines.append(
                f"  Диск: {server_data.get('disk_used_gb', 0)}/"
                f"{server_data.get('disk_total_gb', 0)} GB "
                f"({server_data.get('disk_percent', 0)}%)"
            )
            lines.append(f"  Память бота: {server_data.get('bot_memory_mb', 0)} MB")
            lines.append("")
        return lines

    @staticmethod
    def _format_deposits_section(deposits_data: dict) -> list[str]:
        """
        Format deposits details section.

        Args:
            deposits_data: Deposits data dict

        Returns:
            List of formatted deposits section lines
        """
        lines = []
        if deposits_data and not deposits_data.get("error"):
            lines.append("💵 ДЕПОЗИТЫ (детали):")
            lines.append(f"  Сегодня: {deposits_data.get('today_count', 0)} шт (${deposits_data.get('today_amount', 0):,.2f})")
            by_status = deposits_data.get("by_status", {})
            for status, info in by_status.items():
                lines.append(f"  {status}: {info.get('count', 0)} шт (${info.get('amount', 0):,.2f})")
            recent = deposits_data.get("recent", [])
            if recent:
                lines.append("  Последние депозиты:")
                for dep in recent[:5]:
                    lines.append(f"    - ${dep.get('amount', 0):.2f} от @{dep.get('user')} ({dep.get('time')})")
            lines.append("")
        return lines

    @staticmethod
    def _format_withdrawals_section(withdrawals_data: dict) -> list[str]:
        """
        Format withdrawals details section.

        Args:
            withdrawals_data: Withdrawals data dict

        Returns:
            List of formatted withdrawals section lines
        """
        lines = []
        if withdrawals_data and not withdrawals_data.get("error"):
            pending_list = withdrawals_data.get("pending_list", [])
            if pending_list:
                lines.append("⏳ ОЖИДАЮЩИЕ ВЫВОДА:")
                for w in pending_list[:10]:
                    lines.append(f"  - ${w.get('amount', 0):.2f} @{w.get('user')} (ждёт с {w.get('waiting_since')})")
                lines.append("")
        return lines

    @staticmethod
    def _format_transactions_section(txns_data: dict) -> list[str]:
        """
        Format transactions summary section.

        Args:
            txns_data: Transactions data dict

        Returns:
            List of formatted transactions section lines
        """
        lines = []
        if txns_data and not txns_data.get("error"):
            lines.append("📊 ТРАНЗАКЦИИ ЗА 24Ч:")
            for tx_type, info in txns_data.items():
                lines.append(f"  {tx_type}: {info.get('count', 0)} шт (${info.get('total', 0):,.2f})")
            lines.append("")
        return lines

    @staticmethod
    def _format_inquiries_section(inquiries_data: dict) -> list[str]:
        """
        Format user inquiries/support requests section.

        Args:
            inquiries_data: Inquiries data dict

        Returns:
            List of formatted inquiries section lines
        """
        lines = []
        if inquiries_data and inquiries_data.get("available"):
            lines.append("📩 ОБРАЩЕНИЯ ПОЛЬЗОВАТЕЛЕЙ:")
            lines.append(f"  Всего обращений: {inquiries_data.get('total', 0)}")
            lines.append(f"  🆕 Новых (ждут ответа): {inquiries_data.get('new_count', 0)}")
            lines.append(f"  🔄 В работе: {inquiries_data.get('in_progress_count', 0)}")
            lines.append(f"  ✅ Закрыто: {inquiries_data.get('closed_count', 0)}")

            recent_inquiries = inquiries_data.get("recent", [])
            if recent_inquiries:
                lines.append("  Последние обращения:")
                for inq in recent_inquiries[:10]:
                    status_emoji = {"new": "🆕", "in_progress": "🔄", "closed": "✅"}.get(inq.get("status"), "❓")
                    lines.append(
                        f"    {status_emoji} [{inq.get('created')}] "
                        f"@{inq.get('user')}: {inq.get('question', '')[:60]}..."
                    )
                    if inq.get("assigned_to") != "Не назначен":
                        lines.append(f"       → Назначен: @{inq.get('assigned_to')}")
            lines.append("")
        return lines

    @staticmethod
    def _format_system_section(system_data: dict) -> list[str]:
        """
        Format system health section.

        Args:
            system_data: System data dict

        Returns:
            List of formatted system section lines
        """
        lines = []
        lines.append("✅ СТАТУС СИСТЕМЫ:")
        lines.append(f"  База данных: {system_data.get('database', 'N/A')}")
        lines.append(f"  Общий статус: {system_data.get('status', 'N/A')}")
        return lines
