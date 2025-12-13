"""
ARIA Security Defense System.

DEPRECATED: This file is kept for backward compatibility.
Please import from app.services.aria_security instead.

Comprehensive protection against:
1. Prompt Injection Attacks - attempts to override ARIA's instructions
2. Social Engineering - manipulation to gain admin privileges
3. Forwarded Message Attacks - spoofed messages from "admins"
4. Username Spoofing - fake similar usernames
5. Privilege Escalation - attempts to gain higher access
6. Data Exfiltration - attempts to extract sensitive info

CRITICAL: This module is the last line of defense.
All suspicious activity MUST be logged and potentially blocked.
"""

# Re-export everything from the new modular structure
from app.services.aria_security import (
    COMPILED_PATTERNS,
    DATA_EXFILTRATION_PATTERNS,
    PRIVILEGE_ESCALATION_PATTERNS,
    PROMPT_INJECTION_PATTERNS,
    SECURITY_RESPONSE_BLOCKED,
    SECURITY_RESPONSE_FORWARDED,
    SECURITY_RESPONSE_SPOOFING,
    SOCIAL_ENGINEERING_PATTERNS,
    ARIASecurityGuard,
    SecurityAnalyzer,
    ToolRateLimiter,
    check_forwarded_message,
    compile_patterns,
    create_secure_context,
    get_rate_limiter,
    get_security_guard,
    sanitize_user_input,
)

__all__ = [
    # Patterns
    "PROMPT_INJECTION_PATTERNS",
    "SOCIAL_ENGINEERING_PATTERNS",
    "PRIVILEGE_ESCALATION_PATTERNS",
    "DATA_EXFILTRATION_PATTERNS",
    "compile_patterns",
    "COMPILED_PATTERNS",
    # Responses
    "SECURITY_RESPONSE_BLOCKED",
    "SECURITY_RESPONSE_FORWARDED",
    "SECURITY_RESPONSE_SPOOFING",
    # Analyzers
    "SecurityAnalyzer",
    # Validators
    "sanitize_user_input",
    "create_secure_context",
    "check_forwarded_message",
    # Security Guard
    "ARIASecurityGuard",
    "get_security_guard",
    # Rate Limiter
    "ToolRateLimiter",
    "get_rate_limiter",
]
