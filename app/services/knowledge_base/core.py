"""Core Knowledge Base class."""

from .crud import CRUDMixin
from .formatting import FormattingMixin
from .search import SearchMixin
from .storage import StorageMixin


class KnowledgeBase(StorageMixin, CRUDMixin, SearchMixin, FormattingMixin):
    """Main Knowledge Base class combining all functionality.

    This class uses multiple mixins to organize functionality:
    - StorageMixin: Loading and saving to JSON
    - CRUDMixin: Create, Read, Update, Delete operations
    - SearchMixin: Search and filtering
    - FormattingMixin: Output formatting for AI

    Usage:
        kb = KnowledgeBase()
        kb.add_entry("Question?", "Answer", category="General")
        results = kb.search("question")
    """

    def __init__(self) -> None:
        """Initialize Knowledge Base and load data."""
        super().__init__()
        self.load()


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    """Get singleton instance of Knowledge Base.

    Returns:
        Global KnowledgeBase instance
    """
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
