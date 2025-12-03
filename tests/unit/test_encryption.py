"""Unit tests for encryption utilities."""

import pytest
from cryptography.fernet import Fernet

from app.utils.encryption import EncryptionService


class TestEncryption:
    """Tests for encryption/decryption utilities."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encryption and decryption should be reversible."""
        key = Fernet.generate_key().decode()
        service = EncryptionService(key)

        original_data = "test_sensitive_data_123"
        encrypted = service.encrypt(original_data)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original_data
        assert encrypted != original_data

    def test_encrypt_produces_different_output(self):
        """Same input encrypted twice should produce different outputs."""
        key = Fernet.generate_key().decode()
        service = EncryptionService(key)

        data = "test_data"
        encrypted1 = service.encrypt(data)
        encrypted2 = service.encrypt(data)

        # Due to random IV, outputs should be different
        assert encrypted1 != encrypted2

    def test_decrypt_both_versions(self):
        """Both encrypted versions should decrypt to same original."""
        key = Fernet.generate_key().decode()
        service = EncryptionService(key)

        data = "test_data"
        encrypted1 = service.encrypt(data)
        encrypted2 = service.encrypt(data)

        assert service.decrypt(encrypted1) == data
        assert service.decrypt(encrypted2) == data

    def test_empty_string_encryption(self):
        """Empty string should be encryptable."""
        key = Fernet.generate_key().decode()
        service = EncryptionService(key)

        encrypted = service.encrypt("")
        decrypted = service.decrypt(encrypted)
        assert decrypted == ""

    def test_unicode_encryption(self):
        """Unicode strings should be properly encrypted."""
        key = Fernet.generate_key().decode()
        service = EncryptionService(key)

        original = "Привет мир! 🌍"
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)
        assert decrypted == original

    def test_invalid_encrypted_data_returns_none(self):
        """Decrypting invalid data should return None."""
        key = Fernet.generate_key().decode()
        service = EncryptionService(key)

        result = service.decrypt("invalid_encrypted_data")
        assert result is None
