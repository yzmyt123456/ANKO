"""DND 词条(名词词典)API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Request

from anko.glossary import find_entries, linkify, list_entries
from anko.schemas.glossary import (
    GlossaryEntryRead,
    LinkifyRequest,
    LinkifyResponse,
    LinkSegment,
)

router = APIRouter(prefix="/glossary", tags=["DND 词条"])


@router.get("", response_model=list[GlossaryEntryRead])
def glossary(
    category: Optional[str] = Query(
        None, description="按分类过滤: attribute/skill/spell/class/rule/equipment"
    ),
    q: Optional[str] = Query(None, description="按名称搜索"),
    request: Request = None,
) -> list[GlossaryEntryRead]:
    """内置 DND 词条列表(标注本地知识库命中)。"""
    entries = list_entries(category)
    if q:
        entries = [e for e in entries if q in e["name"]]
    rule_svc = request.app.state.rule_service
    result = []
    for e in entries:
        hit = rule_svc.resolve_term(e["name"])
        result.append(
            GlossaryEntryRead(
                **e, local=hit["local"], local_type=hit["type"]
            )
        )
    return result


@router.post("/linkify", response_model=LinkifyResponse)
def linkify_text(payload: LinkifyRequest) -> LinkifyResponse:
    """把文本中的 DND 专有名词标注为可链接片段。"""
    segments = linkify(payload.text)
    hits = [
        s["entry"]["name"]
        for s in segments
        if s["entry"] is not None
    ]
    return LinkifyResponse(
        segments=[LinkSegment(**s) for s in segments],
        hits=hits,
    )
