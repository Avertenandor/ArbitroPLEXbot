"""
Bot Initialization - Handlers Module.

Module: handlers.py
Registers all bot handlers (user and admin).
Handler order matters for proper routing.
"""

from aiogram import Dispatcher
from loguru import logger

from bot.middlewares.admin_auth_middleware import AdminAuthMiddleware


def register_user_handlers(dp: Dispatcher) -> None:
    """Register all user handlers."""
    from bot.handlers import (
        account_recovery,
        appeal,
        calculator,
        common,
        contact_update,
        deposit,
        finpass_recovery,
        help,
        inquiry,
        instructions,
        language,
        menu,
        profile,
        referral,
        sponsor_inquiry_referral,
        sponsor_inquiry_sponsor,
        start,
        support,
        transaction,
        verification,
        wallet_change,
        withdrawal,
    )

    # Core handlers - menu must be registered BEFORE deposit/withdrawal
    # to have priority over FSM state handlers
    dp.include_router(start.router)

    # Help command - early to catch /help in any state
    dp.include_router(help.router)

    # Common handlers (cancel button) - MUST be early to catch cancel in any state
    dp.include_router(common.router)

    dp.include_router(menu.router)

    # User handlers (registered AFTER menu to ensure menu handlers
    # process menu buttons first, even if user is in FSM state)
    dp.include_router(contact_update.router)  # Contact update with buttons
    dp.include_router(wallet_change.router)
    dp.include_router(deposit.router)
    dp.include_router(withdrawal.router)
    dp.include_router(referral.router)
    dp.include_router(calculator.router)
    dp.include_router(profile.router)
    dp.include_router(transaction.router)
    dp.include_router(support.router)
    dp.include_router(verification.router)
    dp.include_router(finpass_recovery.router)
    dp.include_router(account_recovery.router)  # R16-3: Account recovery
    dp.include_router(language.router)  # R13-3: Language selection
    dp.include_router(instructions.router)
    dp.include_router(appeal.router)

    # User inquiry handler (questions to admins)
    dp.include_router(inquiry.router)

    # Sponsor inquiry handlers (referral-to-sponsor communication)
    dp.include_router(sponsor_inquiry_referral.router)
    dp.include_router(sponsor_inquiry_sponsor.router)

    # CloudSonet 4.5 AI Assistant handler
    from bot.handlers import cloudsonet_ai
    dp.include_router(cloudsonet_ai.router)

    logger.info("User handlers registered successfully")


def register_admin_handlers(dp: Dispatcher) -> None:
    """Register all admin handlers with authentication middleware."""
    from bot.handlers.admin import (
        action_logs,
        admins,
        ai_assistant,
        blacklist,
        blockchain_settings,
        broadcast,
        deposit_management,
        deposit_settings,
        emergency,
        financials,
        inquiries,
        master_key_management,
        panel,
        referral_stats,
        roi_corridor,
        user_messages,
        users,
        wallet_key_setup,
        wallet_management,
        wallets,
        withdrawal_settings,
        withdrawals,
    )
    from bot.handlers.admin import finpass_recovery as admin_finpass
    from bot.handlers.admin import schedule_management
    from bot.handlers.admin import support as admin_support

    # Master key management (only for super admin telegram_id: 1040687384)
    # NOTE: This router does NOT use AdminAuthMiddleware because it's used
    # to GET the master key, so it can't require master key authentication
    # MUST be registered BEFORE menu.router to have priority
    dp.include_router(master_key_management.router)

    # ROI corridor router MUST be before menu.router to handle FSM states
    dp.include_router(roi_corridor.router)

    # Admin handlers (wallet_key_setup must be first for security)
    # Apply AdminAuthMiddleware to all admin routers
    admin_auth_middleware = AdminAuthMiddleware()

    # Apply middleware to admin routers
    _apply_admin_auth(admin_auth_middleware, [
        wallet_key_setup,
        panel,
        users,
        withdrawals,
        withdrawal_settings,
        blockchain_settings,
        financials,
        broadcast,
        blacklist,
        deposit_settings,
        deposit_management,
        roi_corridor,
        admin_finpass,
        wallets,
        wallet_management,
        admins,
        admin_support,
        user_messages,
        emergency,
        inquiries,
        action_logs,
        schedule_management,
        ai_assistant,  # Added: AI Assistant for admins
    ])

    dp.include_router(wallet_key_setup.router)
    # MUST be before panel.router to catch "💰 Финансовая отчётность"
    dp.include_router(financials.router)
    # MUST be before panel.router for withdrawal buttons
    dp.include_router(withdrawals.router)
    dp.include_router(panel.router)
    dp.include_router(users.router)
    dp.include_router(withdrawal_settings.router)
    dp.include_router(blockchain_settings.router)
    dp.include_router(broadcast.router)
    dp.include_router(blacklist.router)
    dp.include_router(deposit_settings.router)
    dp.include_router(deposit_management.router)
    # roi_corridor.router already registered before menu.router for FSM priority
    dp.include_router(admin_finpass.router)
    dp.include_router(wallets.router)
    dp.include_router(wallet_management.router)
    dp.include_router(admins.router)
    dp.include_router(admin_support.router)
    dp.include_router(user_messages.router)
    dp.include_router(emergency.router)  # R17-3: Emergency stop controls
    dp.include_router(inquiries.router)
    dp.include_router(action_logs.router)  # Admin action logs viewer
    dp.include_router(schedule_management.router)  # Schedule management
    dp.include_router(ai_assistant.router)  # AI Assistant for admins

    # Admin referral stats handler
    referral_stats.router.message.middleware(admin_auth_middleware)
    dp.include_router(referral_stats.router)

    logger.info("Admin handlers registered successfully")


def register_fallback_handlers(dp: Dispatcher) -> None:
    """Register fallback and debug handlers."""
    from bot.handlers import debug_unhandled, fallback

    # Fallback handler for orphaned states (must be BEFORE debug_unhandled)
    dp.include_router(fallback.router)

    # Debug handler (MUST BE LAST to catch unhandled messages)
    dp.include_router(debug_unhandled.router)

    logger.info("Fallback handlers registered successfully")


def _apply_admin_auth(middleware, routers) -> None:
    """Apply admin auth middleware to a list of routers."""
    for router in routers:
        router.router.message.middleware(middleware)
        router.router.callback_query.middleware(middleware)


def register_all_handlers(dp: Dispatcher) -> None:
    """Register all handlers in the correct order."""
    register_user_handlers(dp)
    register_admin_handlers(dp)
    register_fallback_handlers(dp)
