"""Общая инициализация базы данных для задач."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import settings


def create_task_engine():
    """Создает engine для использования в задачах."""
    return create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )


def create_task_session_maker(engine=None):
    """Создает session maker для задач."""
    if engine is None:
        engine = create_task_engine()
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# Готовые к использованию экземпляры
task_engine = create_task_engine()
task_session_maker = create_task_session_maker(task_engine)
