"""
AI Tool Executor - Backward Compatibility Shim.

This file provides backward compatibility for imports from the old path.
The actual implementation has been refactored into the tool_executor/ package.

Original: 1039 lines -> Refactored: 26 modules

Usage (both work):
    from app.services.ai.tool_executor import ToolExecutor  # old
    from app.services.ai.tool_executor import ToolExecutor  # new (same path!)
"""

# Re-export from the new modular structure
from app.services.ai.tool_executor import ToolExecutor

__all__ = ["ToolExecutor"]
