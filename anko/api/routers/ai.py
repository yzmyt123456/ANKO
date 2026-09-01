"""AI 助手 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from anko.ai.client import AIError
from anko.schemas.ai import AIParseRequest, AIStatus, CharacterDraft

router = APIRouter(prefix="/ai", tags=["AI 助手"])


@router.get("/status", response_model=AIStatus)
def ai_status(request: Request) -> AIStatus:
    """查询 AI 服务是否已配置。"""
    service = request.app.state.ai_service
    return AIStatus(enabled=service.enabled, provider=service.provider_desc)


@router.post("/parse-character", response_model=CharacterDraft)
async def parse_character(
    payload: AIParseRequest, request: Request
) -> CharacterDraft:
    """解析一段角色描述为结构化人物卡草稿。"""
    service = request.app.state.ai_service
    if not service.enabled:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI 尚未配置。请在 config/settings.yaml 中设置 "
                "ai.enabled: true 并填写 ai.api_key(支持 DeepSeek / "
                "OpenAI / 通义 / Kimi / Ollama)。"
            ),
        )
    try:
        draft = await service.parse_character(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CharacterDraft(**draft)
