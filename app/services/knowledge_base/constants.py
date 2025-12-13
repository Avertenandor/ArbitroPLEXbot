"""Constants and path utilities for Knowledge Base."""

from pathlib import Path


KB_PATH = Path("/app/data/knowledge_base.json")
KB_PATH_LOCAL = Path("data/knowledge_base.json")


def get_kb_path() -> Path:
    """Get the appropriate KB path based on environment.

    Returns:
        Path to knowledge base JSON file.
    """
    if KB_PATH.parent.exists():
        return KB_PATH
    KB_PATH_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    return KB_PATH_LOCAL
