"""
Pagination utilities.

Provides reusable pagination components for building paginated keyboards
and managing paginated lists.
"""

import math
from collections.abc import Callable
from typing import Any, TypeVar

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

T = TypeVar('T')


class PaginationBuilder:
    """
    Builder for paginated inline keyboards.

    Provides methods to build paginated keyboards with navigation buttons
    and helpers for calculating page information.

    Example:
        ```python
        builder = PaginationBuilder()
        items = ["item1", "item2", ..., "item20"]

        # Build keyboard with pagination
        keyboard = builder.build_keyboard(
            items=items,
            page=1,
            per_page=10,
            callback_prefix="list",
            item_formatter=lambda item, idx: (f"Item {idx}", f"select:{item}")
        )
        ```
    """

    def __init__(
        self,
        prev_text: str = "⬅️ Назад",
        next_text: str = "Вперёд ➡️",
        page_info_text: str = "Стр. {current}/{total}",
    ):
        """
        Initialize pagination builder.

        Args:
            prev_text: Text for "previous page" button
            next_text: Text for "next page" button
            page_info_text: Format string for page info button (optional)
        """
        self.prev_text = prev_text
        self.next_text = next_text
        self.page_info_text = page_info_text

    def get_page_items(
        self,
        items: list[T],
        page: int,
        per_page: int,
    ) -> list[T]:
        """
        Get items for a specific page.

        Args:
            items: Full list of items
            page: Current page number (1-indexed)
            per_page: Number of items per page

        Returns:
            List of items for the requested page
        """
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        return items[start_idx:end_idx]

    def get_total_pages(
        self,
        items: list[Any] | int,
        per_page: int,
    ) -> int:
        """
        Calculate total number of pages.

        Args:
            items: Either a list of items or total count (int)
            per_page: Number of items per page

        Returns:
            Total number of pages
        """
        if isinstance(items, int):
            total_count = items
        else:
            total_count = len(items)

        return math.ceil(total_count / per_page) if total_count > 0 else 1

    def build_navigation_row(
        self,
        current_page: int,
        total_pages: int,
        callback_prefix: str,
        show_page_info: bool = False,
    ) -> list[InlineKeyboardButton]:
        """
        Build navigation row with prev/next buttons.

        Args:
            current_page: Current page number (1-indexed)
            total_pages: Total number of pages
            callback_prefix: Prefix for callback data
            show_page_info: Whether to show page info button between nav buttons

        Returns:
            List of InlineKeyboardButton for navigation
        """
        buttons = []

        # Previous button
        if current_page > 1:
            buttons.append(
                InlineKeyboardButton(
                    text=self.prev_text,
                    callback_data=f"{callback_prefix}:page:{current_page - 1}",
                )
            )

        # Page info (optional, non-clickable)
        if show_page_info:
            page_text = self.page_info_text.format(
                current=current_page,
                total=total_pages,
            )
            buttons.append(
                InlineKeyboardButton(
                    text=page_text,
                    callback_data="noop",  # Non-functional callback
                )
            )

        # Next button
        if current_page < total_pages:
            buttons.append(
                InlineKeyboardButton(
                    text=self.next_text,
                    callback_data=f"{callback_prefix}:page:{current_page + 1}",
                )
            )

        return buttons

    def build_keyboard(
        self,
        items: list[T],
        page: int,
        per_page: int,
        callback_prefix: str,
        item_formatter: Callable[[T, int], tuple[str, str]] | None = None,
        items_per_row: int = 1,
        show_page_info: bool = False,
        extra_buttons: list[list[InlineKeyboardButton]] | None = None,
    ) -> InlineKeyboardMarkup:
        """
        Build paginated inline keyboard with items and navigation.

        Args:
            items: Full list of items to paginate
            page: Current page number (1-indexed)
            per_page: Number of items per page
            callback_prefix: Prefix for navigation callback data
            item_formatter: Function to format item into (text, callback_data).
                          Receives item and its index in the full list.
                          If None, items are expected to be InlineKeyboardButton objects.
            items_per_row: Number of item buttons per row
            show_page_info: Whether to show page info in navigation row
            extra_buttons: Additional button rows to append after navigation

        Returns:
            InlineKeyboardMarkup with paginated items and navigation
        """
        builder = InlineKeyboardBuilder()

        # Get items for current page
        total_pages = self.get_total_pages(items, per_page)
        page_items = self.get_page_items(items, page, per_page)

        # Calculate starting index for this page
        start_idx = (page - 1) * per_page

        # Add item buttons
        if item_formatter:
            # Format items using provided formatter
            for idx, item in enumerate(page_items, start=start_idx):
                text, callback_data = item_formatter(item, idx)
                builder.button(text=text, callback_data=callback_data)
        else:
            # Items are already InlineKeyboardButton objects
            for item in page_items:
                if isinstance(item, InlineKeyboardButton):
                    builder.add(item)
                else:
                    raise ValueError(
                        "Items must be InlineKeyboardButton objects when "
                        "item_formatter is not provided"
                    )

        # Adjust layout for item buttons
        builder.adjust(items_per_row)

        # Add navigation row if needed
        if total_pages > 1:
            nav_buttons = self.build_navigation_row(
                current_page=page,
                total_pages=total_pages,
                callback_prefix=callback_prefix,
                show_page_info=show_page_info,
            )
            builder.row(*nav_buttons)

        # Add extra buttons if provided
        if extra_buttons:
            for button_row in extra_buttons:
                builder.row(*button_row)

        return builder.as_markup()


def paginate_list(
    items: list[T],
    page: int,
    per_page: int,
) -> tuple[list[T], int, int]:
    """
    Helper function to paginate a list.

    Args:
        items: Full list of items
        page: Current page number (1-indexed)
        per_page: Number of items per page

    Returns:
        Tuple of (page_items, total_items, total_pages)
    """
    total_items = len(items)
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

    # Ensure page is within valid range
    page = max(1, min(page, total_pages))

    # Get items for current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_items = items[start_idx:end_idx]

    return page_items, total_items, total_pages


def parse_page_callback(callback_data: str, prefix: str) -> int | None:
    """
    Parse page number from callback data.

    Expected format: "{prefix}:page:{page_number}"

    Args:
        callback_data: Callback data string
        prefix: Expected callback prefix

    Returns:
        Page number if valid, None otherwise
    """
    try:
        parts = callback_data.split(':')
        if len(parts) >= 3 and parts[0] == prefix and parts[1] == 'page':
            return int(parts[2])
    except (ValueError, IndexError) as e:
        # Expected error for malformed callback data
        from loguru import logger
        logger.debug(f"Failed to parse page callback '{callback_data}': {e}")

    return None
