"""所有内置路由的汇总。"""

from fastapi import APIRouter

from anko.api.routers.ai import router as ai_router
from anko.api.routers.characters import router as characters_router
from anko.api.routers.dice import maid_router, roll_router
from anko.api.routers.stories import router as stories_router

# 内置路由(插件路由由应用工厂额外挂载)
api_router = APIRouter()
api_router.include_router(characters_router)
api_router.include_router(stories_router)
api_router.include_router(maid_router)
api_router.include_router(roll_router)
api_router.include_router(ai_router)
