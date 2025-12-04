"""
Base repository.

Generic CRUD operations for all repositories.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

# Generic type for model
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with generic CRUD operations.

    Provides async database operations for any SQLAlchemy model.

    Type Parameters:
        ModelType: SQLAlchemy model class

    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)
    """

    def __init__(
        self, model: type[ModelType], session: AsyncSession
    ) -> None:
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> ModelType | None:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity or None if not found
        """
        return await self.session.get(self.model, id)

    async def get_by(
        self, **filters: Any
    ) -> ModelType | None:
        """
        Get single entity by filters.

        Args:
            **filters: Column filters

        Returns:
            First matching entity or None
        """
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(
        self,
        limit: int | None = None,
        offset: int | None = None,
        **filters: Any,
    ) -> list[ModelType]:
        """
        Find all entities matching filters.

        Args:
            limit: Max number of results
            offset: Number of results to skip
            **filters: Column filters

        Returns:
            List of matching entities
        """
        stmt = select(self.model).filter_by(**filters)

        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by(
        self, **filters: Any
    ) -> list[ModelType]:
        """
        Find entities by filters.

        Args:
            **filters: Column filters

        Returns:
            List of matching entities
        """
        return await self.find_all(**filters)

    async def create(self, **data: Any) -> ModelType:
        """
        Create new entity.

        Args:
            **data: Entity data

        Returns:
            Created entity
        """
        entity = self.model(**data)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(
        self, id: int, for_update: bool = False, **data: Any
    ) -> ModelType | None:
        """
        Update entity by ID.

        Args:
            id: Entity ID
            for_update: Use SELECT FOR UPDATE to lock row (prevents race conditions)
            **data: Updated data

        Returns:
            Updated entity or None if not found
        """
        if for_update:
            # R9-2: Use pessimistic locking to prevent race conditions
            stmt = select(self.model).where(self.model.id == id).with_for_update()
            result = await self.session.execute(stmt)
            entity = result.scalar_one_or_none()
        else:
            entity = await self.get_by_id(id)

        if not entity:
            return None

        for key, value in data.items():
            setattr(entity, key, value)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: int) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def count(self, **filters: Any) -> int:
        """
        Count entities matching filters.

        Args:
            **filters: Column filters

        Returns:
            Count of matching entities
        """
        stmt = select(func.count()).select_from(self.model)

        if filters:
            stmt = stmt.filter_by(**filters)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, **filters: Any) -> bool:
        """
        Check if entity exists.

        Args:
            **filters: Column filters

        Returns:
            True if exists, False otherwise
        """
        count = await self.count(**filters)
        return count > 0

    async def bulk_create(
        self, items: list[dict[str, Any]]
    ) -> list[ModelType]:
        """
        Create multiple entities using RETURNING to avoid N+1 refresh.

        Args:
            items: List of entity data dicts

        Returns:
            List of created entities
        """
        if not items:
            return []

        # Use insert with RETURNING to get all created entities in one query
        from sqlalchemy import insert

        stmt = insert(self.model).values(items).returning(self.model)
        result = await self.session.execute(stmt)
        entities = list(result.scalars().all())

        return entities

    async def find_paginated(
        self,
        page: int = 1,
        per_page: int = 100,
        **filters: Any
    ) -> tuple[list[ModelType], int]:
        """
        Find entities with pagination to avoid OOM.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            **filters: Column filters

        Returns:
            Tuple of (items, total_count)
        """
        # Count total matching records
        count_stmt = select(func.count(self.model.id))
        if filters:
            count_stmt = count_stmt.filter_by(**filters)

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get paginated items
        offset = (page - 1) * per_page
        stmt = select(self.model).filter_by(**filters).offset(offset).limit(per_page)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total
