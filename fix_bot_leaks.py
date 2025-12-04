#!/usr/bin/env python3
"""
Script to fix Bot instance leaks by wrapping them in context managers.
Handles proper indentation for nested blocks.
"""

import re
from pathlib import Path


def fix_deposit_monitoring():
    """Fix deposit_monitoring.py - special case with large nested block."""
    file_path = Path("jobs/tasks/deposit_monitoring.py")

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find the line with Bot creation
    bot_line_idx = None
    for i, line in enumerate(lines):
        if '            bot = Bot(token=settings.telegram_bot_token)' in line:
            bot_line_idx = i
            break

    if bot_line_idx is None:
        print(f"Bot line not found in {file_path}")
        return

    # Find the finally block that closes bot session
    finally_idx = None
    close_idx = None
    for i in range(bot_line_idx, len(lines)):
        if 'finally:' in lines[i]:
            finally_idx = i
        if finally_idx and 'await bot.session.close()' in lines[i]:
            close_idx = i
            break

    if close_idx is None:
        print(f"Bot close line not found in {file_path}")
        return

    # Strategy: Replace bot creation with context manager and fix indentation
    # 1. Replace bot creation line with async with Bot...
    # 2. Increase indentation for all lines between bot creation and finally
    # 3. Remove bot.session.close() line

    new_lines = []
    in_bot_block = False
    skip_close = False

    for i, line in enumerate(lines):
        if i == bot_line_idx:
            # Replace with context manager start
            indent = '            '
            new_lines.append(f'{indent}# FIXED: Use context manager for Bot to prevent session leak\n')
            new_lines.append(f'{indent}async with Bot(token=settings.telegram_bot_token) as bot:\n')
            in_bot_block = True
        elif i == bot_line_idx + 1:
            # Skip empty line after bot creation
            in_bot_block = True
            continue
        elif i == bot_line_idx + 2:
            # This should be "try:" - keep but adjust indentation
            new_lines.append('                try:\n')
        elif in_bot_block and i < finally_idx:
            # Add extra indentation (4 spaces)
            if line.strip():  # Non-empty line
                new_lines.append('    ' + line)
            else:
                new_lines.append(line)
        elif i == close_idx:
            # Skip bot.session.close() line
            skip_close = True
            continue
        else:
            new_lines.append(line)

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

        with open(path, 'r') as f:
            content = f.read()

        # Pattern: bot = Bot(token=...) followed by try block with finally close
        # Replace with: async with Bot(token=...) as bot:

        pattern = r'(\s+)bot = Bot\(token=([^\)]+)\)\n'
        replacement = r'\1# FIXED: Use context manager for Bot to prevent session leak\n\1async with Bot(token=\2) as bot:\n'

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
