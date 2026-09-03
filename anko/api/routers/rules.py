"""本地 DND 规则库 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/rules", tags=["DND 规则库"])


def _svc(request: Request):
    return request.app.state.rule_service


@router.get("/status")
def rules_status(request: Request) -> dict:
    """规则库导入状态。"""
    return _svc(request).stats()


@router.get("/spells")
def list_spells(
    q: Optional[str] = Query(None, description="按名称搜索"),
    limit: int = Query(20, ge=1, le=2000),
    request: Request = None,
) -> list[dict]:
    """法术查询。"""
    return _svc(request).search_spells(q, limit)


@router.get("/spells/{name}")
def get_spell(name: str, request: Request) -> dict:
    """法术详情(按名称)。"""
    obj = _svc(request).get_spell(name)
    if obj is None:
        raise HTTPException(status_code=404, detail="未找到该法术")
    return obj


@router.get("/monsters")
def list_monsters(
    q: Optional[str] = Query(None, description="按名称搜索"),
    limit: int = Query(20, ge=1, le=2000),
    request: Request = None,
) -> list[dict]:
    """怪物查询。"""
    return _svc(request).search_monsters(q, limit)


@router.get("/monsters/{name}")
def get_monster(name: str, request: Request) -> dict:
    """怪物详情(按名称)。"""
    obj = _svc(request).get_monster(name)
    if obj is None:
        raise HTTPException(status_code=404, detail="未找到该怪物")
    return obj


@router.get("/books")
def list_books(request: Request) -> list[str]:
    """知识库包含的书籍列表。"""
    return _svc(request).list_books()


@router.get("/categories")
def list_categories(
    book: Optional[str] = Query(None, description="按书籍过滤"),
    request: Request = None,
) -> list[str]:
    """知识片段分类列表。"""
    return _svc(request).list_categories(book)


@router.get("/knowledge")
def list_knowledge_items(
    book: Optional[str] = Query(None, description="按书籍过滤"),
    category: Optional[str] = Query(None, description="按分类过滤"),
    kind: Optional[str] = Query(None, description="按卡片类型过滤"),
    limit: int = Query(60, ge=1, le=200),
    request: Request = None,
) -> list[dict]:
    """按书籍/分类列出知识片段(轻量列表)。"""
    return _svc(request).list_knowledge(book, category, kind, limit)


@router.get("/knowledge/{kid}")
def get_knowledge_item(kid: int, request: Request) -> dict:
    """单条知识片段全文。"""
    obj = _svc(request).get_knowledge(kid)
    if obj is None:
        raise HTTPException(status_code=404, detail="未找到该知识片段")
    return obj


@router.get("/mentions")
def find_mentions(
    text: str = Query(..., min_length=2),
    limit: int = Query(24, ge=1, le=60),
    request: Request = None,
) -> list[dict]:
    """从一段正文里发现知识库词条(法术/怪物/规则标题),供内联悬浮。"""
    return _svc(request).find_mentions(text, limit)


@router.get("/maps")
def list_maps(request: Request) -> list[dict]:
    """地图素材列表。"""
    return _svc(request).list_maps()


@router.get("/search")
def search_knowledge(
    q: str = Query(..., min_length=1),
    book: Optional[str] = Query(None, description="按书籍过滤"),
    category: Optional[str] = Query(None, description="按分类过滤"),
    limit: int = Query(5, ge=1, le=20),
    request: Request = None,
) -> list[dict]:
    """全文检索玩家手册知识片段。"""
    return _svc(request).search_knowledge(q, limit, book, category)
