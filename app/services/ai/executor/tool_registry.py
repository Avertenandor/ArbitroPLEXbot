"""
Tool Registry for AI Tool Executor.

Defines sets of tool names for different categories.
"""


class ToolRegistryMixin:
    """Mixin providing tool name registries for different categories."""

    def _get_messaging_tool_names(self) -> set[str]:
        """Get messaging/broadcast tool names."""
        return {
            "send_message_to_user",
            "broadcast_to_group",
            "get_users_list",
            "invite_to_dialog",
            "mass_invite_to_dialog",
            "send_feedback_request",
            "broadcast_to_admins",
        }

    def _get_appeals_tool_names(self) -> set[str]:
        """Get appeals tool names."""
        return {
            "get_appeals_list",
            "get_appeal_details",
            "take_appeal",
            "resolve_appeal",
            "reply_to_appeal",
        }

    def _get_inquiries_tool_names(self) -> set[str]:
        """Get inquiries tool names."""
        return {
            "get_inquiries_list",
            "get_inquiry_details",
            "take_inquiry",
            "reply_to_inquiry",
            "close_inquiry",
        }

    def _get_user_tool_names(self) -> set[str]:
        """Get user management tool names."""
        return {
            "get_user_profile",
            "search_users",
            "change_user_balance",
            "block_user",
            "unblock_user",
            "get_user_deposits",
            "get_users_stats",
        }

    def _get_stats_tool_names(self) -> set[str]:
        """Get statistics tool names."""
        return {
            "get_deposit_stats",
            "get_bonus_stats",
            "get_withdrawal_stats",
            "get_financial_report",
            "get_roi_stats",
        }

    def _get_withdrawals_tool_names(self) -> set[str]:
        """Get withdrawals tool names."""
        return {
            "get_pending_withdrawals",
            "get_withdrawal_details",
            "approve_withdrawal",
            "reject_withdrawal",
            "get_withdrawals_statistics",
        }

    def _get_system_tool_names(self) -> set[str]:
        """Get system administration tool names."""
        return {
            "get_emergency_status",
            "emergency_full_stop",
            "emergency_full_resume",
            "toggle_emergency_deposits",
            "toggle_emergency_withdrawals",
            "toggle_emergency_roi",
            "get_blockchain_status",
            "switch_rpc_provider",
            "toggle_rpc_auto_switch",
            "get_platform_health",
            "get_global_settings",
        }

    def _get_admin_mgmt_tool_names(self) -> set[str]:
        """Get admin management tool names."""
        return {
            "get_admins_list",
            "get_admin_details",
            "block_admin",
            "unblock_admin",
            "change_admin_role",
            "get_admin_stats",
        }

    def _get_deposits_tool_names(self) -> set[str]:
        """Get deposits tool names."""
        return {
            "get_deposit_levels_config",
            "get_user_deposits_list",
            "get_pending_deposits",
            "get_deposit_details",
            "get_platform_deposit_stats",
            "change_max_deposit_level",
            "create_manual_deposit",
            "modify_deposit_roi",
            "cancel_deposit",
            "confirm_deposit",
        }

    def _get_blacklist_tool_names(self) -> set[str]:
        """Get blacklist tool names."""
        return {
            "get_blacklist",
            "check_blacklist",
            "add_to_blacklist",
            "remove_from_blacklist",
        }

    def _get_finpass_tool_names(self) -> set[str]:
        """Get finpass recovery tool names."""
        return {
            "get_finpass_requests",
            "get_finpass_request_details",
            "approve_finpass_request",
            "reject_finpass_request",
            "get_finpass_stats",
        }

    def _get_referral_tool_names(self) -> set[str]:
        """Get referral tool names."""
        return {
            "get_platform_referral_stats",
            "get_user_referrals",
            "get_top_referrers",
            "get_top_earners",
        }

    def _get_logs_tool_names(self) -> set[str]:
        """Get logs tool names."""
        return {
            "get_recent_logs",
            "get_admin_activity",
            "search_logs",
            "get_action_types_stats",
        }

    def _get_settings_tool_names(self) -> set[str]:
        """Get settings tool names."""
        return {
            "get_withdrawal_settings",
            "set_min_withdrawal",
            "toggle_daily_limit",
            "set_daily_limit",
            "toggle_auto_withdrawal",
            "set_service_fee",
            "get_deposit_settings",
            "set_level_corridor",
            "toggle_deposit_level",
            "set_plex_rate",
            "get_scheduled_tasks",
            "trigger_task",
            "create_admin",
            "delete_admin",
        }
