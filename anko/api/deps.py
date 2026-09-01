"""API 依赖注入:从 app.state 获取服务实例。"""

from __future__ import annotations

from fastapi import Request

from anko.services import CharacterService, DiceService, StoryService


def get_character_service(request: Request) -> CharacterService:
    return request.app.state.character_service


def get_story_service(request: Request) -> StoryService:
    return request.app.state.story_service


def get_dice_service(request: Request) -> DiceService:
    return request.app.state.dice_service
