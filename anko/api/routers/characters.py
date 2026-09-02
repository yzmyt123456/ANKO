"""人物卡 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from anko.api.deps import get_character_service
from anko.schemas.character import (
    CharacterCreate,
    CharacterRead,
    CharacterUpdate,
    CheckRequest,
    CheckResponse,
)
from anko.services import CharacterService

router = APIRouter(prefix="/characters", tags=["人物卡"])


@router.post("", response_model=CharacterRead, status_code=201)
def create_character(
    payload: CharacterCreate,
    service: CharacterService = Depends(get_character_service),
) -> CharacterRead:
    return service.create(payload.model_dump())


@router.get("", response_model=list[CharacterRead])
def list_characters(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    name: Optional[str] = Query(None, description="按名字精确过滤"),
    template: Optional[str] = Query(None, description="按模板过滤"),
    service: CharacterService = Depends(get_character_service),
) -> list[CharacterRead]:
    return service.list(offset=offset, limit=limit, name=name, template=template)


@router.get("/{character_id}", response_model=CharacterRead)
def get_character(
    character_id: int,
    service: CharacterService = Depends(get_character_service),
) -> CharacterRead:
    obj = service.get(character_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="人物卡不存在")
    return obj


@router.put("/{character_id}", response_model=CharacterRead)
def update_character(
    character_id: int,
    payload: CharacterUpdate,
    service: CharacterService = Depends(get_character_service),
) -> CharacterRead:
    obj = service.update(
        character_id, payload.model_dump(exclude_unset=True)
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="人物卡不存在")
    return obj


@router.delete("/{character_id}", status_code=204)
def delete_character(
    character_id: int,
    service: CharacterService = Depends(get_character_service),
) -> None:
    if not service.delete(character_id):
        raise HTTPException(status_code=404, detail="人物卡不存在")


@router.post("/{character_id}/checks", response_model=CheckResponse)
def perform_check(
    character_id: int,
    payload: CheckRequest,
    service: CharacterService = Depends(get_character_service),
) -> CheckResponse:
    """执行 DND 鉴定(属性/技能/豁免),支持 DC 判定。"""
    try:
        result = service.perform_check(
            character_id, payload.kind, payload.key, payload.dc
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CheckResponse(**result)
