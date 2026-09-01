"""AI 助手相关 API 模型。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AIParseRequest(BaseModel):
    """AI 解析请求:粘贴的原始文本。"""

    text: str = Field(..., min_length=1, description="要解析的原始文本")


class CharacterDraft(BaseModel):
    """AI 解析出的人物卡草稿。"""

    name: str = Field(..., description="角色名")
    title: Optional[str] = Field(None, description="称号/职业")
    bio: Optional[str] = Field(None, description="背景概括")
    attributes: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class AIStatus(BaseModel):
    """AI 服务状态。"""

    enabled: bool
    provider: str
