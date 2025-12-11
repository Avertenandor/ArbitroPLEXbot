"""
AI Tool Executor Package.

Modular tool execution system for ARIA AI assistant.
Replaces the monolithic tool_executor.py with registry-based dispatch.
"""

from .executor import ToolExecutor
from .base import BaseToolHandler, HandlerContext, ToolResult
from .registry import ToolRegistry
from .services import ServiceRegistry

__all__ = [
    "ToolExecutor",
    "BaseToolHandler",
    "HandlerContext",
    "ToolResult",
    "ToolRegistry",
    "ServiceRegistry",
]
