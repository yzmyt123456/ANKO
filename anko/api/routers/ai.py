"""AI 助手 API(含运行时配置管理)。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from anko.ai import AIService
from anko.ai.client import AIError
from anko.config import AISettings
from anko.schemas.ai import AIParseRequest, AIStatus, CharacterDraft

router = APIRouter(prefix="/ai", tags=["AI 助手"])


class AIConfigUpdate(BaseModel):
    """AI 配置更新请求(部分字段)。"""

    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None  # 传入新 key 则更新;传掩码/空串保留
    model: Optional[str] = None
    timeout: Optional[float] = None


class AITestRequest(BaseModel):
    """测试连接请求:可携带表单当前填写(未保存)的配置。"""

    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout: Optional[float] = None


@router.get("/status", response_model=AIStatus)
def ai_status(request: Request) -> AIStatus:
    """查询 AI 服务是否已配置。"""
    service = request.app.state.ai_service
    return AIStatus(enabled=service.enabled, provider=service.provider_desc)


@router.get("/config")
def get_ai_config(request: Request) -> dict:
    """读取当前 AI 配置(api_key 已掩码)。"""
    config_service = request.app.state.config_service
    return config_service.get_ai_config(request.app.state.settings.ai)


@router.put("/config")
def update_ai_config(
    payload: AIConfigUpdate, request: Request
) -> dict:
    """更新 AI 配置并立即生效。"""
    config_service = request.app.state.config_service
    return config_service.update_ai_config(
        payload.model_dump(exclude_none=True),
        request.app.state.settings.ai,
    )


@router.post("/test")
async def test_ai(
    request: Request, payload: Optional[AITestRequest] = None
) -> dict:
    """测试 AI 连接。

    支持携带表单当前填写的配置(未保存),用指定配置直接测试;
    不携带时使用已保存的配置。
    """
    service = request.app.state.ai_service

    if payload is not None:
        fields = payload.model_dump(exclude_none=True)
        if fields:
            # 以"已保存配置"为基底,叠加表单当前值
            base = service._current().model_dump()  # noqa: SLF001
            base.update(fields)
            tmp = AIService(AISettings(**base))
            if not tmp.enabled:
                raise HTTPException(
                    status_code=400,
                    detail="请开启 AI 并填写 API Key 后再测试",
                )
            return await tmp.test_connection()

    if not service.enabled:
        raise HTTPException(
            status_code=400,
            detail="请开启 AI 并填写 API Key(可先测试再保存)",
        )
    return await service.test_connection()


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
                "AI 尚未配置。请到「设置」页填写 AI 服务地址、API Key 与模型,"
                "或编辑 config/settings.yaml(支持 DeepSeek / OpenAI / 通义 / Kimi / Ollama)。"
            ),
        )
    try:
        draft = await service.parse_character(payload.text, payload.template)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CharacterDraft(**draft)
