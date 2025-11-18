from collections.abc import AsyncGenerator
import os
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlmodel import SQLModel
from utils.get_env import get_db_directory_env

from models.sql.async_presentation_generation_status import (
    AsyncPresentationGenerationTaskModel,
)
from models.sql.image_asset import ImageAsset
from models.sql.key_value import KeyValueSqlModel
from models.sql.ollama_pull_status import OllamaPullStatus
from models.sql.presentation import PresentationModel
from models.sql.slide import SlideModel
from models.sql.presentation_layout_code import PresentationLayoutCodeModel
from models.sql.template import TemplateModel
from models.sql.webhook_subscription import WebhookSubscription
from utils.db_utils import get_database_url_and_connect_args


# Lazy initialization - engines created on first access
_sql_engine: AsyncEngine | None = None
_async_session_maker = None
_container_db_engine: AsyncEngine | None = None
_container_db_async_session_maker = None


def _get_sql_engine() -> AsyncEngine:
    """Lazy initialization of main database engine."""
    global _sql_engine, _async_session_maker
    if _sql_engine is None:
        database_url, connect_args = get_database_url_and_connect_args()
        _sql_engine = create_async_engine(database_url, connect_args=connect_args)
        _async_session_maker = async_sessionmaker(_sql_engine, expire_on_commit=False)
    return _sql_engine


def _get_container_db_engine() -> AsyncEngine:
    """Lazy initialization of container database engine."""
    global _container_db_engine, _container_db_async_session_maker
    if _container_db_engine is None:
        db_dir = get_db_directory_env() or "/tmp/presenton"
        os.makedirs(db_dir, exist_ok=True)
        # For absolute paths: sqlite+aiosqlite:/// + /absolute/path = sqlite+aiosqlite:////absolute/path
        container_db_url = "sqlite+aiosqlite:///" + os.path.join(db_dir, "container.db")
        _container_db_engine = create_async_engine(
            container_db_url, connect_args={"check_same_thread": False}
        )
        _container_db_async_session_maker = async_sessionmaker(
            _container_db_engine, expire_on_commit=False
        )
    return _container_db_engine


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session for main database."""
    _get_sql_engine()  # Ensure engine is initialized
    async with _async_session_maker() as session:
        yield session


async def get_container_db_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session for container database."""
    _get_container_db_engine()  # Ensure engine is initialized
    async with _container_db_async_session_maker() as session:
        yield session


# Create Database and Tables
async def create_db_and_tables():
    """Initialize database tables. Engines are created lazily on first access."""
    sql_engine = _get_sql_engine()
    container_db_engine = _get_container_db_engine()
    
    async with sql_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.create_all(
                sync_conn,
                tables=[
                    PresentationModel.__table__,
                    SlideModel.__table__,
                    KeyValueSqlModel.__table__,
                    ImageAsset.__table__,
                    PresentationLayoutCodeModel.__table__,
                    TemplateModel.__table__,
                    WebhookSubscription.__table__,
                    AsyncPresentationGenerationTaskModel.__table__,
                ],
            )
        )

    async with container_db_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.create_all(
                sync_conn,
                tables=[OllamaPullStatus.__table__],
            )
        )
