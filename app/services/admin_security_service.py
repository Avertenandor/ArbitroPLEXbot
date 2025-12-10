"""
Admin Security Service.

Provides anti-spoofing protection for admin identification.
Detects attempts to impersonate admins via similar usernames.

SECURITY FEATURES:
1. Username similarity detection (Levenshtein distance)
2. Homoglyph detection (similar looking characters)
3. Admin verification by telegram_id ONLY
4. Suspicious activity logging
5. Alert on spoofing attempts
"""

import re
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin


# Known admin telegram IDs - authoritative source
# SECURITY: This is the ONLY source of truth for admin verification
# Admins are identified ONLY by telegram_id, NEVER by username!
VERIFIED_ADMIN_IDS = {
    1040687384: {"username": "VladarevInvestBrok", "role": "super_admin", "name": "Командир"},
    1691026253: {"username": "AI_XAN", "role": "extended_admin", "name": "Саша (Tech Deputy)"},
    241568583: {"username": "natder", "role": "extended_admin", "name": "Наташа"},
    6540613027: {"username": "ded_vtapkax", "role": "extended_admin", "name": "Влад"},
}

# Homoglyphs - characters that look similar
HOMOGLYPHS = {
    'a': ['а', 'ά', 'α', '@', '4'],  # Latin a, Cyrillic а, Greek α
    'e': ['е', 'ё', 'ε', '3'],  # Latin e, Cyrillic е/ё, Greek ε
    'o': ['о', 'ο', '0'],  # Latin o, Cyrillic о, Greek ο
    'p': ['р', 'ρ'],  # Latin p, Cyrillic р, Greek ρ
    'c': ['с', 'ς'],  # Latin c, Cyrillic с, Greek ς
    'x': ['х', 'χ'],  # Latin x, Cyrillic х, Greek χ
    'y': ['у', 'γ'],  # Latin y, Cyrillic у
    'i': ['і', 'ι', '1', 'l', '|'],  # Latin i, Ukrainian і, Greek ι
    'k': ['к'],  # Latin k, Cyrillic к
    'n': ['п'],  # Can look similar in some fonts
    'm': ['м'],
    't': ['т'],
    'h': ['н'],  # Can look similar
    'b': ['ь', 'б'],
    'd': ['д'],
    'v': ['ν', 'v'],  # Greek nu
    'w': ['ш', 'щ'],
    's': ['ѕ'],  # Cyrillic ѕ
    'u': ['υ', 'ц'],  # Greek upsilon
    'A': ['А', 'Α'],  # Latin A, Cyrillic А, Greek Α
    'B': ['В', 'Β'],  # Latin B, Cyrillic В, Greek Β
    'E': ['Е', 'Ε'],  # Latin E, Cyrillic Е, Greek Ε
    'K': ['К', 'Κ'],  # Latin K, Cyrillic К, Greek Κ
    'M': ['М', 'Μ'],  # Latin M, Cyrillic М, Greek Μ
    'H': ['Н', 'Η'],  # Latin H, Cyrillic Н, Greek Η
    'O': ['О', 'Ο', '0'],  # Latin O, Cyrillic О, Greek Ο
    'P': ['Р', 'Ρ'],  # Latin P, Cyrillic Р, Greek Ρ
    'C': ['С', 'Ϲ'],  # Latin C, Cyrillic С
    'T': ['Т', 'Τ'],  # Latin T, Cyrillic Т, Greek Τ
    'X': ['Х', 'Χ'],  # Latin X, Cyrillic Х, Greek Χ
    'Y': ['У', 'Υ'],  # Latin Y, Cyrillic У, Greek Υ
    'r': ['р'],  # Latin r, Cyrillic р (ADDED)
    '_': ['-', '.'],  # Underscore variations (FIXED: removed empty string)
}


def normalize_username(username: str) -> str:
    """
    Normalize username by replacing homoglyphs with base characters.
    Returns lowercase normalized version.
    """
    if not username:
        return ""

    result = username.lower()

    # Replace homoglyphs
    for base_char, similar_chars in HOMOGLYPHS.items():
        for similar in similar_chars:
            result = result.replace(similar.lower(), base_char.lower())

    # Remove special characters
    result = re.sub(r'[^a-z0-9]', '', result)

    return result


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def username_similarity(username1: str, username2: str) -> float:
    """
    Calculate similarity between two usernames (0.0 to 1.0).
    Takes into account homoglyphs and Levenshtein distance.
    """
    if not username1 or not username2:
        return 0.0

    # Normalize both usernames
    norm1 = normalize_username(username1)
    norm2 = normalize_username(username2)

    if norm1 == norm2:
        return 1.0

    # Calculate Levenshtein distance on normalized versions
    max_len = max(len(norm1), len(norm2))
    if max_len == 0:
        return 0.0

    distance = levenshtein_distance(norm1, norm2)
    similarity = 1.0 - (distance / max_len)

    return similarity


class AdminSecurityService:
    """
    Admin security and anti-spoofing service.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def verify_admin_identity(
        self, telegram_id: int, username: str | None = None
    ) -> dict[str, Any]:
        """
        Verify admin identity by telegram_id.
        Check for spoofing attempts if username provided.
        
        Returns:
            dict with verification result and any warnings
        """
        result = {
            "is_verified_admin": False,
            "admin_info": None,
            "warnings": [],
            "spoofing_detected": False,
            "similar_to_admin": None,
        }

        # Check if telegram_id is in verified admin list
        if telegram_id in VERIFIED_ADMIN_IDS:
            admin_info = VERIFIED_ADMIN_IDS[telegram_id]
            result["is_verified_admin"] = True
            result["admin_info"] = {
                "telegram_id": telegram_id,
                "expected_username": admin_info["username"],
                "role": admin_info["role"],
                "name": admin_info["name"],
            }

            # Check if username matches expected
            if username:
                expected = admin_info["username"].lower()
                actual = username.lower()
                if actual != expected:
                    result["warnings"].append(
                        f"⚠️ Username изменён! Ожидался @{admin_info['username']}, "
                        f"получен @{username}"
                    )
                    logger.warning(
                        f"ADMIN SECURITY: Admin {telegram_id} username mismatch! "
                        f"Expected: {admin_info['username']}, Got: {username}"
                    )
        else:
            # Not a verified admin - check for spoofing attempts
            if username:
                spoof_check = self._check_username_spoofing(username, telegram_id)
                if spoof_check["is_spoofing"]:
                    result["spoofing_detected"] = True
                    result["similar_to_admin"] = spoof_check["similar_to"]
                    result["warnings"].append(spoof_check["warning"])

                    logger.error(
                        f"🚨 SPOOFING ATTEMPT DETECTED! "
                        f"User {telegram_id} (@{username}) trying to impersonate "
                        f"admin @{spoof_check['similar_to']}"
                    )

        return result

    def _check_username_spoofing(
        self, username: str, telegram_id: int
    ) -> dict[str, Any]:
        """
        Check if username is attempting to spoof an admin.
        """
        result = {
            "is_spoofing": False,
            "similar_to": None,
            "similarity": 0.0,
            "warning": None,
        }

        # Check against all known admin usernames
        for admin_id, admin_info in VERIFIED_ADMIN_IDS.items():
            if admin_id == telegram_id:
                continue  # Skip self

            admin_username = admin_info["username"]
            similarity = username_similarity(username, admin_username)

            # Threshold for spoofing detection
            # 0.7 = 70% similarity triggers warning
            # 0.9 = 90% similarity is almost certain spoofing
            if similarity >= 0.7:
                result["is_spoofing"] = True
                result["similar_to"] = admin_username
                result["similarity"] = similarity

                if similarity >= 0.9:
                    result["warning"] = (
                        f"🚨 КРИТИЧНО: Username @{username} почти идентичен "
                        f"админу @{admin_username} (сходство: {similarity*100:.0f}%)"
                    )
                else:
                    result["warning"] = (
                        f"⚠️ ПОДОЗРЕНИЕ: Username @{username} похож на "
                        f"админа @{admin_username} (сходство: {similarity*100:.0f}%)"
                    )
                break

        return result

    async def get_all_verified_admins(self) -> list[dict[str, Any]]:
        """Get list of all verified admins."""
        admins = []
        for telegram_id, info in VERIFIED_ADMIN_IDS.items():
            admins.append({
                "telegram_id": telegram_id,
                "username": f"@{info['username']}",
                "role": info["role"],
                "name": info["name"],
            })
        return admins

    async def check_user_for_spoofing(
        self, telegram_id: int, username: str | None
    ) -> str | None:
        """
        Quick check for spoofing. Returns warning message if detected.
        """
        if not username:
            return None

        verification = await self.verify_admin_identity(telegram_id, username)

        if verification["spoofing_detected"]:
            return verification["warnings"][0] if verification["warnings"] else None

        return None

    def format_secure_admin_display(
        self, telegram_id: int, username: str | None
    ) -> str:
        """
        Format admin display with security indicators.
        Always shows telegram_id for verification.
        """
        # Check if this is a verified admin
        if telegram_id in VERIFIED_ADMIN_IDS:
            admin_info = VERIFIED_ADMIN_IDS[telegram_id]
            return f"✅ @{admin_info['username']} (ID: {telegram_id})"

        # Unknown user - show with warning
        if username:
            return f"❓ @{username} (ID: {telegram_id}) [НЕ ВЕРИФИЦИРОВАН]"

        return f"❓ ID: {telegram_id} [НЕ ВЕРИФИЦИРОВАН]"


# Quick check function for use in handlers
async def check_spoofing(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
) -> str | None:
    """
    Quick spoofing check. Returns warning if spoofing detected.
    """
    security = AdminSecurityService(session)
    return await security.check_user_for_spoofing(telegram_id, username)


# Test function
def test_similarity():
    """Test username similarity detection."""
    test_cases = [
        ("ded_vtapkax", "DeDvTapkax", "Case change"),
        ("ded_vtapkax", "ded_vtapkаx", "Cyrillic а"),  # а is Cyrillic!
        ("ded_vtapkax", "dеd_vtapkax", "Cyrillic е"),  # е is Cyrillic!
        ("ded_vtapkax", "ded_vtapkax_", "Extra char"),
        ("ded_vtapkax", "ded-vtapkax", "Underscore to dash"),
        ("ded_vtapkax", "dedvtapkax", "No underscore"),
        ("VladarevInvestBrok", "VIadarevInvestBrok", "l vs I"),
        ("VladarevInvestBrok", "V1adarevInvestBrok", "l vs 1"),
        ("natder", "nаtder", "Cyrillic а"),  # а is Cyrillic!
    ]

    print("Username Similarity Tests:")
    print("-" * 60)
    for original, spoofed, description in test_cases:
        sim = username_similarity(original, spoofed)
        norm_orig = normalize_username(original)
        norm_spoof = normalize_username(spoofed)
        print(f"{description}:")
        print(f"  Original: {original} -> {norm_orig}")
        print(f"  Spoofed:  {spoofed} -> {norm_spoof}")
        print(f"  Similarity: {sim*100:.1f}%")
        print()


if __name__ == "__main__":
    test_similarity()
