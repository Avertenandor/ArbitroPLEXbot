"""Knowledge Base package for ARIA AI Assistant.

This package provides a modular knowledge base system organized into:
- constants: Path configuration
- data: Default knowledge base entries
- storage: JSON loading/saving operations
- crud: Create, Read, Update, Delete operations
- search: Search and filtering functionality
- formatting: Output formatting for AI
- core: Main KnowledgeBase class

For backward compatibility, import from this module:
    from app.services.knowledge_base import (
        KnowledgeBase,
        get_knowledge_base
    )
"""

from .core import KnowledgeBase, get_knowledge_base

__all__ = ["KnowledgeBase", "get_knowledge_base"]
