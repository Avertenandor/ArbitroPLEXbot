"""Text utility functions for bot."""

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from loguru import logger


def escape_markdown(text: str) -> str:
    """
    Escape Markdown special characters to prevent parse errors.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for Markdown parsing
    """
    # Escape special Markdown characters
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def strip_markdown(text: str) -> str:
    """
    Remove Markdown formatting from text.

    Args:
        text: Text with Markdown formatting

    Returns:
        Plain text without Markdown
    """
    # Remove bold/italic markers
    result = text.replace('*', '').replace('_', '')
    # Remove code markers
    result = result.replace('`', '')
    # Remove escape characters
    result = result.replace('\\', '')
    return result


def sanitize_markdown(text: str) -> str:
    """
    Sanitize text to prevent Telegram Markdown parse errors.
    Fixes unclosed formatting and escapes problematic characters.
    """
    if not text:
        return text

    # Count formatting characters
    # Fix unclosed bold markers
    bold_count = text.count("**")
    if bold_count % 2 != 0:
        # Remove the last unpaired **
        last_idx = text.rfind("**")
        text = text[:last_idx] + text[last_idx + 2:]

    # Fix unclosed single asterisks (italic)
    # First, temporarily replace ** with placeholder
    text = text.replace("**", "\x00BOLD\x00")
    asterisk_count = text.count("*")
    if asterisk_count % 2 != 0:
        # Remove the last unpaired *
        last_idx = text.rfind("*")
        text = text[:last_idx] + text[last_idx + 1:]
    # Restore bold markers
    text = text.replace("\x00BOLD\x00", "**")

    # Fix unclosed underscores
    # Replace __ with placeholder first
    text = text.replace("__", "\x00UNDER\x00")
    underscore_count = text.count("_")
    if underscore_count % 2 != 0:
        last_idx = text.rfind("_")
        text = text[:last_idx] + text[last_idx + 1:]
    text = text.replace("\x00UNDER\x00", "__")

    # Fix unclosed backticks
    # Handle code blocks first (```)
    code_block_count = text.count("```")
    if code_block_count % 2 != 0:
        text += "\n```"

    # Handle inline code (single `)
    text = text.replace("```", "\x00CODE\x00")
    backtick_count = text.count("`")
    if backtick_count % 2 != 0:
        last_idx = text.rfind("`")
        text = text[:last_idx] + text[last_idx + 1:]
    text = text.replace("\x00CODE\x00", "```")

    # Fix unclosed square brackets (links)
    open_brackets = text.count("[")
    close_brackets = text.count("]")
    if open_brackets > close_brackets:
        text += "]" * (open_brackets - close_brackets)

    return text


async def safe_answer(
    message: Message,
    text: str,
    parse_mode: str = "Markdown",
    **kwargs
) -> Message | None:
    """
    Safely send a message with fallback if Markdown parsing fails.

    Args:
        message: Message to reply to
        text: Text to send
        parse_mode: Parse mode (Markdown, HTML, or None)
        **kwargs: Additional arguments for message.answer()

    Returns:
        Sent message or None if failed
    """
    try:
        return await message.answer(text, parse_mode=parse_mode, **kwargs)
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e):
            logger.warning(f"Markdown parse error, sending without formatting: {e}")
            # Try without parse_mode
            try:
                plain_text = strip_markdown(text)
                return await message.answer(plain_text, **kwargs)
            except Exception as e2:
                logger.error(f"Failed to send plain text: {e2}")
                return None
        raise
