"""DND 词条相关 API 模型。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class GlossaryEntryRead(BaseModel):
    """一个 DND 词条。"""

    name: str
    category: str
    category_label: str
    url: str


class LinkifyRequest(BaseModel):
    """文本链接化请求。"""

    text: str = Field(..., min_length=1, description="原始文本")


class LinkSegment(BaseModel):
    """文本片段(命中的词条带 entry)。"""

    text: str
    entry: Optional[GlossaryEntryRead] = None


class LinkifyResponse(BaseModel):
    """文本链接化结果:片段序列。"""

    segments: list[LinkSegment]
    hits: list[str] = Field(default_factory=list, description="命中的词条名")
