"""AI 助手 API(含运行时配置管理)。"""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from anko.ai import AIService
from anko.ai import dm as dm_assets
from anko.ai import corpus as corpus_assets
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


class GenerateCharacterRequest(BaseModel):
    """AI 生成角色请求。"""

    story_context: Optional[str] = Field(
        None, description="故事世界观/已写剧情摘要"
    )
    hint: Optional[str] = Field(None, description="对角色的一句话想法(可选)")
    template: str = Field("dnd5e", description="目标模板: default / dnd5e")
    partial: Optional[str] = Field(
        None, description="已生成(可能被中断)的文本,用于从断点继续"
    )


class StorySegmentRequest(BaseModel):
    """逐段续写安科正文请求。"""

    context: Optional[str] = Field("", description="当前正文(玩家可编辑后传入)")
    cast: Optional[str] = Field("", description="登场角色卡片摘要")
    instruction: Optional[str] = Field("", description="本段指示(可空)")
    roll_note: Optional[str] = Field("", description="最近一次掷骰结果文本")
    persona: Optional[str] = Field(None, description="导游人格 id(缺省用楼主式)")


class DMAnkaiRequest(BaseModel):
    """安价起草请求:让导游以读者口吻给出候选选项。"""

    topic: str = Field(..., min_length=1, description="安价主题")
    context: Optional[str] = Field("", description="当前正文")
    cast: Optional[str] = Field("", description="登场角色")
    count: int = Field(6, ge=2, le=12, description="候选条数")
    persona: Optional[str] = Field(None, description="导游人格 id")


class DMProposeRequest(BaseModel):
    """导游提案请求:让 AI 判断下一步是叙述、掷骰还是抛回给玩家。"""

    context: Optional[str] = Field("", description="当前正文")
    cast: Optional[str] = Field("", description="登场角色卡片摘要")
    instruction: Optional[str] = Field("", description="玩家倾向/遭遇提示(可空)")
    roll_note: Optional[str] = Field("", description="最近一次掷骰结果文本")
    persona: Optional[str] = Field(None, description="导游人格 id(缺省用楼主式)")


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


@router.post("/generate-character/stream")
async def generate_character_stream(
    payload: GenerateCharacterRequest, request: Request
) -> StreamingResponse:
    """流式生成角色(SSE):实时推送增量文本,支持从断点继续。"""
    service = request.app.state.ai_service
    if not service.enabled:
        raise HTTPException(
            status_code=503,
            detail="AI 尚未配置。请到「设置」页填写 AI 服务地址、API Key 与模型。",
        )

    async def event_stream():
        buffer = payload.partial or ""
        # 检索本地规则参考
        extra_rules = ""
        try:
            rule_svc = request.app.state.rule_service
            refs = []
            for kw in ("六项属性", "种族", "阵营", "职业", "属性值"):
                refs += rule_svc.search_knowledge(kw, limit=1)
            seen = set()
            parts = []
            for r in refs:
                key = r["page"]
                if key in seen:
                    continue
                seen.add(key)
                parts.append(f"[玩家手册 p{r['page']}]{r['content'][:220]}")
            extra_rules = "\n".join(parts[:4])
        except Exception:  # noqa: BLE001
            extra_rules = ""
        try:
            async for delta in service.generate_character_stream(
                story_context=payload.story_context or "",
                hint=payload.hint or "",
                template=payload.template,
                partial=buffer,
                extra_rules=extra_rules,
            ):
                buffer += delta
                yield f"data: {json.dumps({'type': 'delta', 'text': delta}, ensure_ascii=False)}\n\n"
            # 结束后拆分过程文本与 JSON,解析为草稿
            from anko.ai.service import (
                extract_json,
                normalize_character_draft,
                normalize_dnd_draft,
                split_process_and_json,
            )

            process_text, json_part = split_process_and_json(buffer)
            data = extract_json(json_part or buffer)
            draft = (
                normalize_dnd_draft(data)
                if payload.template == "dnd5e"
                else normalize_character_draft(data)
            )
            if not draft.get("name"):
                raise ValueError("AI 未能生成角色名,请重试")
            yield (
                f"data: {json.dumps({'type': 'done', 'draft': draft, 'process': process_text}, ensure_ascii=False)}\n\n"
            )
        except (ValueError, AIError) as exc:
            yield (
                f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
            )
        except Exception as exc:  # noqa: BLE001
            yield (
                f"data: {json.dumps({'type': 'error', 'message': f'生成失败:{exc}'}, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate-segment/stream")
async def generate_segment_stream(
    payload: StorySegmentRequest, request: Request
) -> StreamingResponse:
    """逐段续写安科正文(SSE):正文可被玩家在段落之间自由修改后继续。"""
    service = request.app.state.ai_service
    if not service.enabled:
        raise HTTPException(
            status_code=503,
            detail="AI 尚未配置。请到「设置」页填写 AI 服务地址、API Key 与模型。",
        )

    async def event_stream():
        try:
            # 从知识库检索与当前角色/判定相关的参考片段
            extra_rules = ""
            try:
                rule_svc = request.app.state.rule_service
                kws = ["职业", "种族", "属性", "检定", "安科"]
                refs = []
                for kw in kws:
                    refs += rule_svc.search_knowledge(kw, limit=1)
                seen = set()
                parts = []
                for r in refs:
                    key = r.get("page")
                    if key in seen:
                        continue
                    seen.add(key)
                    parts.append(
                        f"[玩家手册 p{r.get('page')} {r.get('title', '')[:24]}]\n"
                        f"{(r.get('content') or '')[:300]}"
                    )
                extra_rules = "\n\n".join(parts[:4])
            except Exception:  # noqa: BLE001 知识库缺失不阻断生成
                extra_rules = ""
            async for delta in service.generate_story_segment_stream(
                context=payload.context or "",
                cast=payload.cast or "",
                instruction=payload.instruction or "",
                roll_note=payload.roll_note or "",
                extra_rules=extra_rules,
                persona_id=payload.persona or dm_assets.PERSONA_ID,
            ):
                yield f"data: {json.dumps({'type': 'delta', 'text': delta}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        except (ValueError, AIError) as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': f'生成失败:{exc}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/dm/personas")
def dm_personas() -> dict:
    """可选的导游人格列表 + 楼主语料检索规模。"""
    return {"personas": dm_assets.build_dm_persona_list(), "corpus": corpus_assets.corpus_stats()}


@router.post("/dm/ankai-draft")
async def dm_ankai_draft(payload: DMAnkaiRequest, request: Request) -> dict:
    """安价起草:导游以读者口吻给出一批候选(玩家/导游再编辑确认)。"""
    service = request.app.state.ai_service
    if not service.enabled:
        raise HTTPException(
            status_code=503,
            detail="AI 尚未配置。请到「设置」页填写 AI 服务地址、API Key 与模型。",
        )
    try:
        return await service.dm_ankai_draft(
            topic=payload.topic,
            context=payload.context or "",
            cast=payload.cast or "",
            count=payload.count,
            persona_id=payload.persona or dm_assets.PERSONA_ID,
        )
    except (ValueError, AIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/dm/propose")
async def dm_propose(payload: DMProposeRequest, request: Request) -> dict:
    """导游提案:自动判断下一步该掷骰、叙述还是交还玩家(玩家确认后才执行)。"""
    service = request.app.state.ai_service
    if not service.enabled:
        raise HTTPException(
            status_code=503,
            detail="AI 尚未配置。请到「设置」页填写 AI 服务地址、API Key 与模型。",
        )
    extra_rules = ""
    try:
        rule_svc = request.app.state.rule_service
        kws = ["检定", "豁免", "规则", "安科"]
        refs = []
        for kw in kws:
            refs += rule_svc.search_knowledge(kw, limit=1)
        parts = []
        seen = set()
        for r in refs:
            key = r.get("page")
            if key in seen:
                continue
            seen.add(key)
            parts.append(f"[规则库 p{r.get('page')}] {r.get('title', '')[:24]}\n{(r.get('content') or '')[:300]}")
        extra_rules = "\n\n".join(parts[:4])
    except Exception:  # noqa: BLE001 规则库缺失不阻断
        extra_rules = ""
    try:
        return await service.dm_propose(
            context=payload.context or "",
            cast=payload.cast or "",
            instruction=payload.instruction or "",
            roll_note=payload.roll_note or "",
            extra_rules=extra_rules,
            persona_id=payload.persona or dm_assets.PERSONA_ID,
        )
    except (ValueError, AIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/generate-character", response_model=CharacterDraft)
async def generate_character(
    payload: GenerateCharacterRequest, request: Request
) -> CharacterDraft:
    """用"骰点创建法"生成一位角色(结合当前故事设定)。"""
    service = request.app.state.ai_service
    if not service.enabled:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI 尚未配置。请到「设置」页填写 AI 服务地址、API Key 与模型。"
            ),
        )
    try:
        draft = await service.generate_character(
            story_context=payload.story_context or "",
            hint=payload.hint or "",
            template=payload.template,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CharacterDraft(**draft)


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
