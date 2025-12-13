"""
AI Assistant Service Module.

Refactored from monolithic ai_assistant_service.py into modular components.

Modules:
    - core: Main AIAssistantService class
    - message_builder: System prompt and context building
    - model_selector: Model selection logic
    - knowledge_extractor: Knowledge extraction and saving
    - tool_processor: Tool execution for admin and user commands

Usage:
    from app.services.ai_assistant import (
        AIAssistantService,
        get_ai_service,
    )
"""

from .core import AIAssistantService, get_ai_service

__all__ = [
    "AIAssistantService",
    "get_ai_service",
]
