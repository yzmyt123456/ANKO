"""骰娘与掷骰相关 API 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class MaidCreate(BaseModel):
    """创建自定义骰娘。"""

    name: str = Field(..., min_length=1, max_length=100, description="骰娘名")
    personality: Optional[str] = Field(None, description="人设/性格/说话风格")
    greeting: Optional[str] = Field(None, description="开场白")
    default_expression: str = Field("1d100", description="默认骰子表达式")
    settings: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "规则配置,如 {'threshold': 50, 'crit_success': 95,"
            " 'crit_fail': 5, 'modifiers': [...]}"
        ),
    )
    extra: dict[str, Any] = Field(default_factory=dict)


class MaidUpdate(BaseModel):
    name: Optional[str] = None
    personality: Optional[str] = None
    greeting: Optional[str] = None
    default_expression: Optional[str] = None
    settings: Optional[dict[str, Any]] = None
    extra: Optional[dict[str, Any]] = None


class MaidRead(BaseModel):
    id: int
    name: str
    personality: Optional[str]
    greeting: Optional[str]
    default_expression: str
    settings: dict[str, Any]
    is_system: bool
    extra: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RollRequest(BaseModel):
    """一次掷骰请求。"""

    expression: Optional[str] = Field(
        None, description="骰子表达式,如 '1d100'、'2d6+3';为空时使用骰娘默认"
    )
    maid_id: Optional[int] = Field(None, description="骰娘 id;为空使用默认骰娘")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="关联上下文,如 {'story_id': 1, 'character_id': 2}",
    )
    note: Optional[str] = Field(None, description="备注")
    save: bool = Field(True, description="是否保存掷骰记录")


class RollRead(BaseModel):
    id: int
    maid_id: Optional[int]
    expression: str
    total: int
    details: list[dict[str, Any]]
    judgement: Optional[dict[str, Any]]
    context: dict[str, Any]
    note: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RollResponse(BaseModel):
    """掷骰响应:记录 + 人类可读描述。"""

    record: RollRead
    description: str
