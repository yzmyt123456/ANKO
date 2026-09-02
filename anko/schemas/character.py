"""人物卡相关 API 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="人物名")
    title: Optional[str] = Field(None, max_length=200, description="称号")
    avatar: Optional[str] = Field(None, max_length=500, description="头像 URL")
    bio: Optional[str] = Field(None, description="人物背景")
    template: str = Field(
        "default", max_length=50, description="人物卡模板: default / dnd5e"
    )
    stats: dict[str, Any] = Field(
        default_factory=dict, description="模板结构化字段(如 DND 六属性/AC/法术)"
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="通用自由属性,如 {'力量': 18}"
    )
    tags: list[str] = Field(default_factory=list, description="标签")
    extra: dict[str, Any] = Field(default_factory=dict, description="扩展字段")


class CharacterCreate(CharacterBase):
    """创建人物卡。"""


class CharacterUpdate(BaseModel):
    """更新人物卡(部分字段,None 表示不修改)。"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    template: Optional[str] = None
    stats: Optional[dict[str, Any]] = None
    attributes: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    extra: Optional[dict[str, Any]] = None


class CharacterRead(CharacterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CheckRequest(BaseModel):
    """一次 DND 鉴定请求。"""

    kind: str = Field(..., description="鉴定类型: stat / skill / save")
    key: str = Field(..., description="鉴定项 key,如 strength / perception / save_dexterity")
    dc: Optional[int] = Field(None, ge=1, le=100, description="目标 DC,提供时判定成功/失败")


class CheckResponse(BaseModel):
    """一次鉴定的结果。"""

    character_id: int
    label: str
    kind: str
    expression: str
    natural: int
    modifier: int
    total: int
    judgement: Optional[dict[str, Any]] = None
    description: str


class TemplateRead(BaseModel):
    """人物卡模板定义。"""

    id: str
    name: str
    description: str
    groups: list[dict[str, Any]]
    checks: list[dict[str, Any]] = Field(default_factory=list)
