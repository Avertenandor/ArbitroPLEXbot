#!/usr/bin/env python3
"""
Script to fix Bot instance leaks by wrapping them in context managers.
Handles proper indentation for nested blocks.
"""

import re
from pathlib import Path


def _find_bot_line(lines):
    """Find the line index where Bot is created."""
    for i, line in enumerate(lines):
        if '            bot = Bot(token=settings.telegram_bot_token)' in line:
            return i
    return None


def _find_bot_close_lines(lines, start_idx):
    """Find the finally block and bot.session.close() line indices."""
    finally_idx = None
    close_idx = None

    for i in range(start_idx, len(lines)):
        if 'finally:' in lines[i]:
            finally_idx = i
        if finally_idx and 'await bot.session.close()' in lines[i]:
            close_idx = i
            break

    return finally_idx, close_idx


def _process_line_for_bot_block(i, line, bot_line_idx, finally_idx, close_idx):
    """Process a single line during bot block transformation."""
    if i == bot_line_idx:
        # Replace with context manager start
        indent = '            '
        return [
            f'{indent}# FIXED: Use context manager for Bot to prevent session leak\n',
            f'{indent}async with Bot(token=settings.telegram_bot_token) as bot:\n'
        ], True

    if i == bot_line_idx + 1:
        # Skip empty line after bot creation
        return [], True

    if i == bot_line_idx + 2:
        # This should be "try:" - keep but adjust indentation
        return ['                try:\n'], True

    if i < finally_idx:
        # Add extra indentation (4 spaces) for non-empty lines
        if line.strip():
            return ['    ' + line], True
        return [line], True

    if i == close_idx:
        # Skip bot.session.close() line
        return [], False

    return [line], False


def _transform_lines_for_bot_context(lines, bot_line_idx, finally_idx, close_idx):
    """Transform lines to use Bot context manager."""
    new_lines = []

    for i, line in enumerate(lines):
        processed_lines, _ = _process_line_for_bot_block(
            i, line, bot_line_idx, finally_idx, close_idx
        )
        new_lines.extend(processed_lines)

    return new_lines


def fix_deposit_monitoring():
    """Fix deposit_monitoring.py - special case with large nested block."""
    file_path = Path("jobs/tasks/deposit_monitoring.py")

    with open(file_path) as f:
        lines = f.readlines()

    # Find the line with Bot creation
    bot_line_idx = _find_bot_line(lines)
    if bot_line_idx is None:
        print(f"Bot line not found in {file_path}")
        return

    # Find the finally block that closes bot session
    finally_idx, close_idx = _find_bot_close_lines(lines, bot_line_idx)
    if close_idx is None:
        print(f"Bot close line not found in {file_path}")
        return

    # Transform lines to use context manager
    new_lines = _transform_lines_for_bot_context(
        lines, bot_line_idx, finally_idx, close_idx
    )

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

    print(f"Fixed {file_path}")


def fix_simple_bot_files():
    """Fix files with simpler Bot usage patterns."""
    files = [
        "jobs/tasks/notification_retry.py",
        "jobs/tasks/financial_reconciliation.py",
        "jobs/tasks/stuck_transaction_monitor.py",
        "jobs/tasks/node_health_monitor.py",
        "jobs/tasks/plex_payment_monitor.py",
        "scripts/notify_admin.py",
    ]

    for file_path in files:
        path = Path(file_path)
        if not path.exists():
            print(f"Skipping {file_path} - not found")
            continue

        with open(path) as f:
            content = f.read()

        # Pattern: bot = Bot(token=...) followed by try block with finally close
        # Replace with: async with Bot(token=...) as bot:

        pattern = r'(\s+)bot = Bot\(token=([^\)]+)\)\n'
        replacement = (
            r'\1# FIXED: Use context manager for Bot to prevent session leak\n'
            r'\1async with Bot(token=\2) as bot:\n'
        )

        new_content = re.sub(pattern, replacement, content)

        # Remove await bot.session.close() lines
        new_content = re.sub(r'\s+await bot\.session\.close\(\)\n', '', new_content)

        # Fix indentation after async with: lines that were inside try block need extra indent
        # This is file-specific and requires careful handling

        with open(path, 'w') as f:
            f.write(new_content)

        print(f"Fixed {file_path}")


if __name__ == "__main__":
    # For now, let's just fix the simple ones manually
    # deposit_monitoring is too complex for automated fix
    print("This script needs to be run carefully per file")
    print("Skipping automated fix - will do manual fixes")
