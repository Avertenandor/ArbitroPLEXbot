"""
Bot Initialization Module.

This module contains all initialization logic split into focused modules:
- logging: Logger configuration
- services: Service initialization (encryption, blockchain)
- storage: FSM storage setup (Redis/PostgreSQL)
- middlewares: Middleware registration
- handlers: Handler registration (user and admin)
- shutdown: Graceful shutdown handler
"""

__all__ = []
