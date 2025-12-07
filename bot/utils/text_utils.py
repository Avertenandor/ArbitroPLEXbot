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

