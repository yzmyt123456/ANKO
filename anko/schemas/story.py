"""剧情 / 故事线相关 API 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class StoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    maid_id: Optional[int] = Field(None, description="默认骰娘 id")
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    maid_id: Optional[int] = None
    tags: Optional[list[str]] = None
    extra: Optional[dict[str, Any]] = None


class StoryRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    maid_id: Optional[int]
    tags: list[str]
    extra: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoryEntryCreate(BaseModel):
    chapter: Optional[str] = Field(None, max_length=100, description="章节/幕")
    content: str = Field(..., min_length=1, description="剧情正文")
    character_ids: list[int] = Field(default_factory=list, description="关联人物卡")
    roll_ids: list[int] = Field(default_factory=list, description="关联掷骰记录")
    extra: dict[str, Any] = Field(default_factory=dict)


class StoryEntryRead(BaseModel):
    id: int
    story_id: int
    chapter: Optional[str]
    content: str
    character_ids: list[int]
    roll_ids: list[int]
    extra: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
