import os

TECH_DEPUTIES = ["AIXAN", "AI_XAN"]

ARYA_AI_ID = 0
ARYA_AI_USERNAME = "ArbitroPLEX_AI"
ARYA_AI_ROLE = "extended_admin"


def _parse_int_list(env_var: str, default: list[int] | None = None) -> list[int]:
    if default is None:
        default = []
    value = os.getenv(env_var, "")
    if not value:
        return default
    return [int(id.strip()) for id in value.split(",") if id.strip()]


SUPER_ADMIN_IDS = _parse_int_list("SUPER_ADMIN_IDS", [])
TRUSTED_ADMIN_IDS = _parse_int_list("TRUSTED_ADMIN_IDS", [])
ARYA_COMMAND_GIVERS = _parse_int_list("ARYA_COMMAND_GIVERS", [])
ARYA_TEACHERS = _parse_int_list("ARYA_TEACHERS", [])
TECH_DEPUTY_TELEGRAM_ID = int(os.getenv("TECH_DEPUTY_TELEGRAM_ID", "0"))


def is_super_admin(telegram_id: int) -> bool:
    """Check if user is a super admin (owner)."""
    return telegram_id in SUPER_ADMIN_IDS


def is_trusted_admin(telegram_id: int) -> bool:
    """Check if user is a trusted admin with elevated privileges."""
    return telegram_id in TRUSTED_ADMIN_IDS


def is_tech_deputy(telegram_id: int | None = None, username: str | None = None) -> bool:
    """
    Check if user is a technical deputy.

    Priority: telegram_id > username
    """
    if telegram_id == TECH_DEPUTY_TELEGRAM_ID:
        return True
    if username and username.replace("@", "") in TECH_DEPUTIES:
        return True
    return False


def can_command_arya(telegram_id: int) -> bool:
    """
    Check if user can give commands to ARYA AI assistant.

    These admins can tell Арья to execute admin operations:
    - Grant/cancel bonuses
    - Send messages to users
    - Broadcast to groups
    - Block/unblock users
    - etc.

    Returns:
        True if user can command Арья
    """
    return telegram_id in ARYA_COMMAND_GIVERS


def can_teach_arya(telegram_id: int) -> bool:
    """
    Check if user can teach ARYA (add to knowledge base).

    Арья will learn from conversations with these admins
    and add new knowledge to her database.

    Returns:
        True if user can teach Арья
    """
    return telegram_id in ARYA_TEACHERS


def get_arya_role() -> str:
    """Get Арья's admin role."""
    return ARYA_AI_ROLE


def is_arya_admin() -> bool:
    """
    Confirm that Арья is an administrator.

    This is used for tool execution - Арья acts as extended_admin
    when executing commands from authorized admins.
    """
    return True  # Арья ВСЕГДА является администратором
