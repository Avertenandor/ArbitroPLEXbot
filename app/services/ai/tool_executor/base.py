"""Base classes and types for the tool executor system.

This module defines the core abstractions for handling tool execution in the AI assistant,
including context management, result structures, and handler interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


__all__ = [
    "HandlerContext",
    "ToolResult",
    "BaseToolHandler",
]


@dataclass
class HandlerContext:
    """Context information passed to tool handlers.

    This dataclass encapsulates all the necessary context that tool handlers
    need to execute operations, including database access, bot interface,
    and admin-specific data.

    Attributes:
        session: Database session for executing queries.
        bot: Telegram bot instance for sending messages and interacting with users.
        admin_data: Dictionary containing admin-specific configuration and data.
        admin_id: Unique identifier for the admin user.
    """
    session: Any
    bot: Any
    admin_data: dict[str, Any]
    admin_id: int


@dataclass
class ToolResult:
    """Result of a tool execution.

    This dataclass represents the outcome of executing a tool, including
    the result content and any error information.

    Attributes:
        type: Type identifier for the result, defaults to "tool_result".
        tool_use_id: Unique identifier for the tool execution instance.
        content: The actual result content or error message.
        is_error: Flag indicating whether the execution resulted in an error.
    """
    tool_use_id: str
    content: str
    type: str = "tool_result"
    is_error: bool = False


class BaseToolHandler(ABC):
    """Abstract base class for tool handlers.

    This class defines the interface that all tool handlers must implement.
    Tool handlers are responsible for executing specific sets of tools and
    managing their lifecycle.

    Attributes:
        context: The handler context containing session, bot, and admin information.
    """

    def __init__(self, context: HandlerContext) -> None:
        """Initialize the tool handler with the given context.

        Args:
            context: Handler context containing necessary execution environment.
        """
        self.context = context

    @abstractmethod
    def get_tool_names(self) -> set[str]:
        """Get the set of tool names that this handler can process.

        Returns:
            A set of tool names that this handler supports.
        """
        pass

    @abstractmethod
    async def handle(self, tool_name: str, tool_input: dict, **kwargs) -> Any:
        """Handle the execution of a specific tool.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing input parameters for the tool.
            **kwargs: Additional keyword arguments for tool execution.

        Returns:
            The result of the tool execution.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        pass

    def can_handle(self, tool_name: str) -> bool:
        """Check if this handler can process the given tool.

        Args:
            tool_name: Name of the tool to check.

        Returns:
            True if this handler supports the tool, False otherwise.
        """
        return tool_name in self.get_tool_names()
