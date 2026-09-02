"""数据库引擎与会话管理。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from anko.config import DatabaseSettings
from anko.models import Base

# 注意:必须导入所有模型,使 metadata 完整(Base 的声明式收集机制)
from anko import models  # noqa: F401


def _ensure_sqlite_dir(url: str) -> None:
    """SQLite 文件型数据库需要保证父目录存在。"""
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        raw = url.removeprefix("sqlite:///")
        db_path = Path(raw)
        db_path.parent.mkdir(parents=True, exist_ok=True)


def build_engine(settings: DatabaseSettings) -> Engine:
    _ensure_sqlite_dir(settings.url)
    kwargs: dict = {"future": True, "echo": settings.echo}
    if settings.url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        # 内存库需要共享同一连接,否则每个会话会看到独立数据库
        if ":memory:" in settings.url:
            from sqlalchemy.pool import StaticPool

            kwargs["poolclass"] = StaticPool
    return create_engine(settings.url, **kwargs)


def create_session_factory(settings: DatabaseSettings) -> sessionmaker[Session]:
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    _run_migrations(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _run_migrations(engine: Engine) -> None:
    """轻量表结构迁移(SQLite)。

    开发期对已存在表补充新列,保证旧数据库可平滑升级。
    """
    with engine.connect() as conn:
        cols = {
            row[1]
            for row in conn.exec_driver_sql(
                "PRAGMA table_info(character_cards)"
            )
        }
        if cols:
            if "template" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE character_cards "
                    "ADD COLUMN template VARCHAR(50) DEFAULT 'default'"
                )
            if "stats" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE character_cards "
                    "ADD COLUMN stats JSON DEFAULT '{}'"
                )
        conn.commit()


def init_db(settings: DatabaseSettings) -> sessionmaker[Session]:
    """初始化数据库并返回会话工厂。"""
    return create_session_factory(settings)


def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """上下文管理器风格的会话迭代器(供测试 / 脚本使用)。"""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
