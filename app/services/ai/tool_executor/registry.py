"""Tool registry for managing tool handlers."""

import logging
from typing import Optional

from .base import BaseToolHandler

__all__ = ["ToolRegistry"]

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing tool handlers with dictionary-based dispatch.

    This class provides a centralized registry for tool handlers, allowing
    efficient lookup and dispatch of tools without using if/elif chains.
    """

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._handlers: dict[str, BaseToolHandler] = {}

    def register_handler(self, handler: BaseToolHandler) -> None:
        """Register all tools from a handler.

        Args:
            handler: The tool handler to register. All tools returned by
                    handler.get_tool_names() will be mapped to this handler.
        """
        tool_names = handler.get_tool_names()
        handler_class_name = handler.__class__.__name__

        for tool_name in tool_names:
            if tool_name in self._handlers:
                existing_handler = self._handlers[tool_name]
                logger.warning(
                    f"Tool '{tool_name}' is already registered to "
                    f"{existing_handler.__class__.__name__}. "
                    f"Overwriting with {handler_class_name}."
                )

            self._handlers[tool_name] = handler
            logger.info(
                f"Registered tool '{tool_name}' to handler {handler_class_name}"
            )

    def get_handler(self, tool_name: str) -> Optional[BaseToolHandler]:
        """Get the handler for a given tool name.

        Args:
            tool_name: The name of the tool to look up.

        Returns:
            The handler for the tool, or None if not registered.
        """
        return self._handlers.get(tool_name)

    def get_all_tool_names(self) -> set[str]:
        """Get all registered tool names.

        Returns:
            A set of all registered tool names.
        """
        return set(self._handlers.keys())

    def is_registered(self, tool_name: str) -> bool:
        """Check if a tool is registered.

        Args:
            tool_name: The name of the tool to check.

        Returns:
            True if the tool is registered, False otherwise.
        """
        return tool_name in self._handlers
