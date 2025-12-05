"""
Backward compatibility module for SystemSettingRepository.

This module re-exports GlobalSettingsRepository as SystemSettingRepository.
All new code should import from app.repositories.global_settings_repository.

Migration:
    Old: from app.repositories.system_setting_repository import SystemSettingRepository
    New: from app.repositories.global_settings_repository import GlobalSettingsRepository
"""

from app.repositories.global_settings_repository import GlobalSettingsRepository

# Alias for backward compatibility
SystemSettingRepository = GlobalSettingsRepository

__all__ = ["SystemSettingRepository"]
