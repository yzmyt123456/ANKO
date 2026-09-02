"""FastAPI 应用工厂。

create_app(settings) 组装全部模块并返回应用实例;
插件在应用创建时自动加载。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from anko.ai import AIService
from anko.api.routers import api_router
from anko.config import Settings, load_settings
from anko.dice.engine import DiceEngine
from anko.plugins.manager import PluginManager
from anko.services import CharacterService, DiceService, StoryService
from anko.storage.database import init_db
from anko.storage.sqlite import SqliteStorage

logger = logging.getLogger("anko")

# 前端静态资源目录
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """创建安科平台应用实例。"""
    settings = settings or load_settings()

    # ---- 基础设施 ----
    session_factory = init_db(settings.database)
    storage = SqliteStorage(session_factory)
    dice_engine = DiceEngine()

    # ---- 业务服务 ----
    character_service = CharacterService(storage, dice_engine)
    story_service = StoryService(storage)
    dice_service = DiceService(
        storage, dice_engine, default_maid_name=settings.dice.default_maid
    )
    dice_service.ensure_default_maid()  # 首次启动时创建内置骰娘
    ai_service = AIService(settings.ai)

    # ---- 应用对象 ----
    app = FastAPI(title=settings.app.name, debug=settings.app.debug)
    app.state.settings = settings
    app.state.storage = storage
    app.state.dice_engine = dice_engine
    app.state.character_service = character_service
    app.state.story_service = story_service
    app.state.dice_service = dice_service
    app.state.ai_service = ai_service

    # ---- 内置路由 ----
    app.include_router(api_router, prefix=settings.server.api_prefix)

    # ---- 前端静态页面 ----
    app.mount(
        "/static", StaticFiles(directory=STATIC_DIR), name="static"
    )

    # ---- 插件 ----
    _load_plugins(app, settings, dice_engine)

    # ---- 基础端点 ----
    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health", tags=["系统"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _load_plugins(
    app: FastAPI, settings: Settings, dice_engine: DiceEngine
) -> list[Any]:
    """加载插件并挂载插件路由。"""

    def get_service(name: str) -> Optional[object]:
        return {
            "character": app.state.character_service,
            "story": app.state.story_service,
            "dice": app.state.dice_service,
        }.get(name)

    manager = PluginManager(
        settings.plugins.directory,
        settings=settings,
        dice_engine=dice_engine,
        get_service=get_service,
    )
    plugins = manager.load()

    api_prefix = settings.server.api_prefix
    for prefix, router in manager.routers:
        app.include_router(router, prefix=f"{api_prefix}{prefix}")

    app.state.plugins = plugins
    logger.info("插件加载完成,共 %d 个", len(plugins))
    return plugins
