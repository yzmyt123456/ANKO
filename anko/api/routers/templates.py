"""人物卡模板 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from anko.schemas.character import TemplateRead
from anko.templates.registry import get_template, list_templates

router = APIRouter(prefix="/templates", tags=["人物卡模板"])


@router.get("", response_model=list[TemplateRead])
def templates() -> list[TemplateRead]:
    """人物卡模板简要列表。"""
    return [TemplateRead(**t) for t in list_templates()]


@router.get("/{template_id}", response_model=TemplateRead)
def template_detail(template_id: str) -> TemplateRead:
    """模板完整定义(分组字段 + 鉴定项)。"""
    t = get_template(template_id)
    if t is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    return TemplateRead(**t.to_dict())
