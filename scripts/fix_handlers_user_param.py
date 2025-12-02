"""
Fix all handlers to use **data pattern for user parameter.

This script automatically converts handlers from:
    async def handler(message: Message, session: AsyncSession, user: User) -> None:
        ...

To:
    async def handler(message: Message, session: AsyncSession, **data: Any) -> None:
        user: User = data.get("user")
        ...
"""

import re
from pathlib import Path


def fix_handler_file(file_path: Path) -> bool:
    """Fix a single handler file."""
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # Check if Any is already imported
    if "from typing import" in content and "Any" not in content:
        # Add Any to existing typing import
        content = re.sub(
            r"(from typing import [^)]+)",
            r"\1, Any",
            content,
            count=1,
        )
    elif "from typing import" not in content:
        # Add new typing import after docstring
        lines = content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if '"""' in line or "'''" in line:
                # Find end of docstring
                quote = '"""' if '"""' in line else "'''"
                count = line.count(quote)
                if count == 2:  # Single-line docstring
                    insert_idx = i + 1
                    break
                elif count == 1:  # Multi-line docstring start
                    for j in range(i + 1, len(lines)):
                        if quote in lines[j]:
                            insert_idx = j + 1
                            break
                    break
        
        if insert_idx > 0:
            lines.insert(insert_idx, "")
            lines.insert(insert_idx + 1, "from typing import Any")
            content = "\n".join(lines)

    # Pattern: find function with user: User parameter
    pattern = r"(async def \w+\([^)]*?)\s+user: User,([^)]*?\)) -> "
    
    def replacer(match):
        before_user = match.group(1)
        after_user = match.group(2)
        
        # Add **data: Any before closing paren
        if after_user.strip() == "":
            # No params after user
            new_signature = f"{before_user}\n    **data: Any,\n{after_user}) -> "
        else:
            # Has params after user
            new_signature = f"{before_user}{after_user[:-1]},\n    **data: Any,\n) -> "
        
        return new_signature
    
    content = re.sub(pattern, replacer, content)

    # Add user extraction at the beginning of functions that were modified
    # Find all function definitions that now have **data
    func_pattern = r"(async def (\w+)\([^)]*\*\*data: Any[^)]*\)) -> None:\n(\s+)(\"\"\"[^\"]*\"\"\")?\n"
    
    def add_user_extraction(match):
        func_def = match.group(1)
        func_name = match.group(2)
        indent = match.group(3)
        docstring = match.group(4) or ""
        
        user_line = f'{indent}user: User = data.get("user")\n'
        
        if docstring:
            return f"{func_def} -> None:\n{indent}{docstring}\n{user_line}"
        else:
            return f"{func_def} -> None:\n{user_line}"
    
    content = re.sub(func_pattern, add_user_extraction, content)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return True
    
    return False


def main():
    """Fix all handler files."""
    handlers_dir = Path(__file__).parent.parent / "bot" / "handlers"
    fixed_files = []
    
    for handler_file in handlers_dir.rglob("*.py"):
        if handler_file.name == "__init__.py":
            continue
        
        print(f"Processing {handler_file.name}...")
        if fix_handler_file(handler_file):
            fixed_files.append(handler_file.name)
            print(f"  ✓ Fixed")
        else:
            print(f"  - No changes needed")
    
    print(f"\nFixed {len(fixed_files)} files:")
    for filename in fixed_files:
        print(f"  - {filename}")


if __name__ == "__main__":
    main()
