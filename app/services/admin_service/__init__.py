"""
Admin Service - Main Package.

This package provides admin authentication and session management services.

Module Structure:
- constants.py: Configuration constants for sessions and rate limiting
- crypto.py: Cryptographic utilities (key generation, hashing, verification)
- admin_manager.py: Admin CRUD operations
- session_manager.py: Session lifecycle management
- rate_limiter.py: Rate limiting and security for login attempts
- service.py: Main AdminService class that orchestrates all operations

Public API:
- AdminService: Main service class for all admin operations

The AdminService class delegates to specialized managers:
- AdminManager: Handles admin creation, retrieval, and deletion
- SessionManager: Manages session creation, validation, and logout
- RateLimiter: Tracks failed logins and enforces rate limits
"""

from .service import AdminService


__all__ = [
    "AdminService",
]
