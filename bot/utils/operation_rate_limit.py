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

        Uses atomic Redis operations to prevent race conditions.

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

            # Атомарная операция через pipeline: инкремент + установка TTL
            pipe = self.redis_client.pipeline()
            pipe.incr(daily_key)
            pipe.expire(daily_key, 86400)  # 24 hours
            pipe.incr(hourly_key)
            pipe.expire(hourly_key, 3600)  # 1 hour
            results = await pipe.execute()

            daily_count = results[0]
            hourly_count = results[2]

            # Проверка дневного лимита (20 per day)
            if daily_count > 20:
                # Откатить инкремент, если превышен лимит
                await self.redis_client.decr(daily_key)
                await self.redis_client.decr(hourly_key)
                return (
                    False,
                    "Превышен дневной лимит заявок на вывод (20/день). "
                    "Попробуйте завтра.",
                )

            # Проверка часового лимита (10 per hour)
            if hourly_count > 10:
                # Откатить инкремент, если превышен лимит
                await self.redis_client.decr(daily_key)
                await self.redis_client.decr(hourly_key)
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

            # Lua скрипт для атомарного инкремента с установкой TTL
            # Возвращает текущее значение счетчика после инкремента
            lua_script = """
            local current = redis.call('INCR', KEYS[1])
            if current == 1 then
                redis.call('EXPIRE', KEYS[1], ARGV[1])
            end
            return current
            """

            # Выполнить атомарную операцию
            current_count = await self.redis_client.eval(
                lua_script, 1, key, window_seconds
            )

            # Проверить лимит
            if current_count > max_attempts:
                # Откатить инкремент, если превышен лимит
                await self.redis_client.decr(key)
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

