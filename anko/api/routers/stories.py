"""剧情 / 故事线 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from anko.api.deps import get_story_service
from anko.schemas.story import (
    StoryCreate,
    StoryEntryCreate,
    StoryEntryRead,
    StoryRead,
    StoryUpdate,
)
from anko.services import StoryService

router = APIRouter(prefix="/stories", tags=["剧情"])


@router.post("", response_model=StoryRead, status_code=201)
def create_story(
    payload: StoryCreate,
    service: StoryService = Depends(get_story_service),
) -> StoryRead:
    return service.create(payload.model_dump())


@router.get("", response_model=list[StoryRead])
def list_stories(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    title: Optional[str] = Query(None, description="按标题精确过滤"),
    service: StoryService = Depends(get_story_service),
) -> list[StoryRead]:
    return service.list(offset=offset, limit=limit, title=title)


@router.get("/{story_id}", response_model=StoryRead)
def get_story(
    story_id: int,
    service: StoryService = Depends(get_story_service),
) -> StoryRead:
    obj = service.get(story_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="故事线不存在")
    return obj


@router.put("/{story_id}", response_model=StoryRead)
def update_story(
    story_id: int,
    payload: StoryUpdate,
    service: StoryService = Depends(get_story_service),
) -> StoryRead:
    obj = service.update(story_id, payload.model_dump(exclude_unset=True))
    if obj is None:
        raise HTTPException(status_code=404, detail="故事线不存在")
    return obj


@router.delete("/{story_id}", status_code=204)
def delete_story(
    story_id: int,
    service: StoryService = Depends(get_story_service),
) -> None:
    if not service.delete(story_id):
        raise HTTPException(status_code=404, detail="故事线不存在")


# ---------- 剧情条目 ----------
@router.post("/{story_id}/entries", response_model=StoryEntryRead, status_code=201)
def add_entry(
    story_id: int,
    payload: StoryEntryCreate,
    service: StoryService = Depends(get_story_service),
) -> StoryEntryRead:
    if service.get(story_id) is None:
        raise HTTPException(status_code=404, detail="故事线不存在")
    return service.add_entry(story_id, payload.model_dump())


@router.get("/{story_id}/entries", response_model=list[StoryEntryRead])
def list_entries(
    story_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: StoryService = Depends(get_story_service),
) -> list[StoryEntryRead]:
    if service.get(story_id) is None:
        raise HTTPException(status_code=404, detail="故事线不存在")
    return service.list_entries(story_id, offset=offset, limit=limit)
