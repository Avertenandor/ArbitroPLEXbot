"""
Keyboard builder utilities.

Reusable keyboard builders for creating Reply and Inline keyboards with fluent API.
"""

from typing import Self

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import (
    InlineKeyboardBuilder as AiogramInlineBuilder,
)
from aiogram.utils.keyboard import (
    ReplyKeyboardBuilder as AiogramReplyBuilder,
)


class ReplyKeyboardBuilder:
    """
    Fluent builder for Reply keyboards with convenience methods.

    Example:
        >>> keyboard = (
        ...     ReplyKeyboardBuilder()
        ...     .add_button("Option 1")
        ...     .add_button("Option 2")
        ...     .add_row("Row 2 Button 1", "Row 2 Button 2")
        ...     .add_back_button()
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        """Initialize the builder."""
        self._builder = AiogramReplyBuilder()

    def add_button(self, text: str) -> Self:
        """
        Add a single button on its own row.

        Args:
            text: Button text

        Returns:
            Self for method chaining
        """
        self._builder.row(KeyboardButton(text=text))
        return self

    def add_row(self, *texts: str) -> Self:
        """
        Add multiple buttons in a single row.

        Args:
            *texts: Button texts to add in the row

        Returns:
            Self for method chaining
        """
        buttons = [KeyboardButton(text=text) for text in texts]
        self._builder.row(*buttons)
        return self

    def add_back_button(self, text: str = "◀️ Назад") -> Self:
        """
        Add a back navigation button.

        Args:
            text: Button text (default: "◀️ Назад")

        Returns:
            Self for method chaining
        """
        self._builder.row(KeyboardButton(text=text))
        return self

    def add_cancel_button(self, text: str = "❌ Отмена") -> Self:
        """
        Add a cancel button.

        Args:
            text: Button text (default: "❌ Отмена")

        Returns:
            Self for method chaining
        """
        self._builder.row(KeyboardButton(text=text))
        return self

    def add_home_button(self, text: str = "🏠 Главное меню") -> Self:
        """
        Add a home/main menu button.

        Args:
            text: Button text (default: "🏠 Главное меню")

        Returns:
            Self for method chaining
        """
        self._builder.row(KeyboardButton(text=text))
        return self

    def build(self, resize: bool = True) -> ReplyKeyboardMarkup:
        """
        Build the final ReplyKeyboardMarkup.

        Args:
            resize: Whether to resize keyboard (default: True)

        Returns:
            ReplyKeyboardMarkup instance
        """
        return self._builder.as_markup(resize_keyboard=resize)


class InlineKeyboardBuilder:
    """
    Wrapper around aiogram's InlineKeyboardBuilder with convenience methods.

    Example:
        >>> keyboard = (
        ...     InlineKeyboardBuilder()
        ...     .add_button("Click me", "callback_data")
        ...     .add_url_button("Visit site", "https://example.com")
        ...     .add_navigation_row("prev", "next", 2, 5)
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        """Initialize the builder."""
        self._builder = AiogramInlineBuilder()

    def add_button(self, text: str, callback_data: str) -> Self:
        """
        Add a single inline button with callback data on its own row.

        Args:
            text: Button text
            callback_data: Callback data to send when pressed

        Returns:
            Self for method chaining
        """
        self._builder.row(
            InlineKeyboardButton(text=text, callback_data=callback_data)
        )
        return self

    def add_url_button(self, text: str, url: str) -> Self:
        """
        Add a URL button on its own row.

        Args:
            text: Button text
            url: URL to open when pressed

        Returns:
            Self for method chaining
        """
        self._builder.row(InlineKeyboardButton(text=text, url=url))
        return self

    def add_navigation_row(
        self,
        prev_callback: str,
        next_callback: str,
        page: int,
        total: int,
    ) -> Self:
        """
        Add a navigation row with previous/next buttons and page indicator.

        Args:
            prev_callback: Callback data for previous button
            next_callback: Callback data for next button
            page: Current page number (1-indexed)
            total: Total number of pages

        Returns:
            Self for method chaining
        """
        buttons = []

        # Add previous button if not on first page
        if page > 1:
            buttons.append(
                InlineKeyboardButton(text="◀️ Пред", callback_data=prev_callback)
            )

        # Add page indicator
        buttons.append(
            InlineKeyboardButton(
                text=f"{page}/{total}", callback_data="page_indicator"
            )
        )

        # Add next button if not on last page
        if page < total:
            buttons.append(
                InlineKeyboardButton(text="След ▶️", callback_data=next_callback)
            )

        self._builder.row(*buttons)
        return self

    def add_row(self, *buttons: tuple[str, str]) -> Self:
        """
        Add a custom row with multiple buttons.

        Args:
            *buttons: Tuples of (text, callback_data) for each button

        Returns:
            Self for method chaining
        """
        inline_buttons = [
            InlineKeyboardButton(text=text, callback_data=callback)
            for text, callback in buttons
        ]
        self._builder.row(*inline_buttons)
        return self

    def build(self) -> InlineKeyboardMarkup:
        """
        Build the final InlineKeyboardMarkup.

        Returns:
            InlineKeyboardMarkup instance
        """
        return self._builder.as_markup()


def quick_reply_keyboard(*buttons: str, resize: bool = True) -> ReplyKeyboardMarkup:
    """
    Create a simple reply keyboard with buttons in a single column.

    Args:
        *buttons: Button texts
        resize: Whether to resize keyboard (default: True)

    Returns:
        ReplyKeyboardMarkup instance

    Example:
        >>> keyboard = quick_reply_keyboard("Option 1", "Option 2", "Cancel")
    """
    builder = AiogramReplyBuilder()
    for text in buttons:
        builder.row(KeyboardButton(text=text))
    return builder.as_markup(resize_keyboard=resize)
