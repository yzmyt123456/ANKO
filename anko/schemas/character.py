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
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="自定义属性组,如 {'力量': 18}"
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
    attributes: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    extra: Optional[dict[str, Any]] = None


class CharacterRead(CharacterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
