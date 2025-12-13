"""
Operation Rate Limiter.

Provides per-operation rate limiting for critical actions:
- Registration
- Verification
- Withdrawal requests
"""

from typing import Any

from loguru import logger


class OperationRateLimiter:
    """
    Rate limiter for critical operations.

    Uses Redis to track attempts per user per operation type.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        """
        Initialize operation rate limiter.

        Args:
            redis_client: Optional Redis client
        """
        self.redis_client = redis_client

    async def check_registration_limit(
        self, telegram_id: int
    ) -> tuple[bool, str | None]:
        """
        Check if user can register (3 attempts per hour).

        Args:
            telegram_id: Telegram user ID

        Returns:
            Tuple of (allowed, error_message)
        """
        return await self._check_limit(
            operation="reg",
            telegram_id=telegram_id,
            max_attempts=3,
            window_seconds=3600,  # 1 hour
            operation_name="регистрация",
        )

    async def check_verification_limit(
        self, telegram_id: int
    ) -> tuple[bool, str | None]:
        """
        Check if user can verify (5 attempts per hour).

        Args:
            telegram_id: Telegram user ID

        Returns:
            Tuple of (allowed, error_message)
        """
        return await self._check_limit(
            operation="verify",
            telegram_id=telegram_id,
            max_attempts=5,
            window_seconds=3600,  # 1 hour
            operation_name="верификация",
        )

    async def check_withdrawal_limit(
        self, telegram_id: int
    ) -> tuple[bool, str | None]:
        """
        Check if user can create withdrawal request.

        Limits:
        - 20 requests per day
        - 10 requests per hour

        Uses atomic Redis Lua script to prevent race conditions.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Tuple of (allowed, error_message)
        """
        if not self.redis_client:
            return True, None  # No Redis, allow

        try:
            daily_key = f"op_limit:withdraw:day:{telegram_id}"
            hourly_key = f"op_limit:withdraw:hour:{telegram_id}"

            # Lua скрипт для атомарной проверки и инкремента обоих лимитов
            # Возвращает: {"daily": count, "hourly": count, "allowed": 0|1}
            lua_script = """
            local daily_key = KEYS[1]
            local hourly_key = KEYS[2]
            local daily_limit = tonumber(ARGV[1])
            local hourly_limit = tonumber(ARGV[2])
            local daily_ttl = tonumber(ARGV[3])
            local hourly_ttl = tonumber(ARGV[4])

            -- Получить текущие значения
            local daily_count = tonumber(redis.call('GET', daily_key) or '0')
            local hourly_count = tonumber(redis.call('GET', hourly_key) or '0')

            -- Проверить лимиты ПЕРЕД инкрементом
            if daily_count >= daily_limit then
                return {daily_count, hourly_count, 0, 'daily'}
            end
            if hourly_count >= hourly_limit then
                return {daily_count, hourly_count, 0, 'hourly'}
            end

            -- Инкрементировать только если лимиты не превышены
            daily_count = redis.call('INCR', daily_key)
            if daily_count == 1 then
                redis.call('EXPIRE', daily_key, daily_ttl)
            end

            hourly_count = redis.call('INCR', hourly_key)
            if hourly_count == 1 then
                redis.call('EXPIRE', hourly_key, hourly_ttl)
            end

            return {daily_count, hourly_count, 1, 'ok'}
            """

            # Выполнить атомарную операцию
            result = await self.redis_client.eval(
                lua_script,
                2,  # 2 keys
                daily_key,
                hourly_key,
                20,  # daily_limit
                10,  # hourly_limit
                86400,  # daily_ttl (24 hours)
                3600,  # hourly_ttl (1 hour)
            )

            daily_count, hourly_count, allowed, limit_type = result

            if not allowed:
                if limit_type == b'daily' or limit_type == 'daily':
                    return (
                        False,
                        "Превышен дневной лимит заявок на вывод (20/день). "
                        "Попробуйте завтра.",
                    )
                else:  # hourly
                    return (
                        False,
                        "Превышен часовой лимит заявок на вывод (10/час). "
                        "Попробуйте позже.",
                    )

            return True, None

        except Exception as e:
            logger.error(f"Error checking withdrawal limit: {e}")
            # Fail open - allow on error
            return True, None

    async def _check_limit(
        self,
        operation: str,
        telegram_id: int,
        max_attempts: int,
        window_seconds: int,
        operation_name: str,
    ) -> tuple[bool, str | None]:
        """
        Check operation rate limit.

        Uses Lua script for atomic operations to prevent race conditions.

        Args:
            operation: Operation type (reg, verify, etc.)
            telegram_id: Telegram user ID
            max_attempts: Maximum attempts allowed
            window_seconds: Time window in seconds
            operation_name: Human-readable operation name

        Returns:
            Tuple of (allowed, error_message)
        """
        if not self.redis_client:
            return True, None  # No Redis, allow

        try:
            key = f"op_limit:{operation}:{telegram_id}"

            # Lua скрипт для атомарной проверки и инкремента
            # Проверяет лимит ПЕРЕД инкрементом, инкрементирует только если разрешено
            # Возвращает: {count, allowed} где allowed = 0|1
            lua_script = """
            local key = KEYS[1]
            local max_attempts = tonumber(ARGV[1])
            local ttl = tonumber(ARGV[2])

            -- Получить текущее значение
            local current = tonumber(redis.call('GET', key) or '0')

            -- Проверить лимит ПЕРЕД инкрементом
            if current >= max_attempts then
                return {current, 0}
            end

            -- Инкрементировать только если лимит не превышен
            current = redis.call('INCR', key)
            if current == 1 then
                redis.call('EXPIRE', key, ttl)
            end

            return {current, 1}
            """

            # Выполнить атомарную операцию
            result = await self.redis_client.eval(
                lua_script, 1, key, max_attempts, window_seconds
            )

            current_count, allowed = result

            # Проверить результат
            if not allowed:
                minutes = window_seconds // 60
                return (
                    False,
                    f"Слишком много попыток {operation_name}. "
                    f"Лимит: {max_attempts} попыток за {minutes} минут. "
                    f"Попробуйте позже.",
                )

            return True, None

        except Exception as e:
            logger.error(f"Error checking {operation} limit: {e}")
            # Fail open - allow on error
            return True, None

    async def clear_limit(
        self, operation: str, telegram_id: int
    ) -> None:
        """
        Clear rate limit for operation (e.g., on success).

        Args:
            operation: Operation type
            telegram_id: Telegram user ID
        """
        if not self.redis_client:
            return

        try:
            key = f"op_limit:{operation}:{telegram_id}"
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Error clearing {operation} limit: {e}")
