"""Knowledge Base for ARIA AI Assistant.

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from: app.services.knowledge_base

Example:
    from app.services.knowledge_base import (
        KnowledgeBase,
        get_knowledge_base
    )
"""

# Re-export everything from the new modular structure
from app.services.knowledge_base import (
    KnowledgeBase,
    get_knowledge_base,
)

__all__ = ["KnowledgeBase", "get_knowledge_base"]
