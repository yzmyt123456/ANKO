"""骰娘与掷骰 API。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from anko.api.deps import get_dice_service
from anko.schemas.dice import (
    MaidCreate,
    MaidRead,
    MaidUpdate,
    RollRead,
    RollRequest,
    RollResponse,
)
from anko.services import DiceService

maid_router = APIRouter(prefix="/maids", tags=["骰娘"])
roll_router = APIRouter(prefix="/rolls", tags=["掷骰"])


# ---------------- 骰娘管理 ----------------
@maid_router.post("", response_model=MaidRead, status_code=201)
def create_maid(
    payload: MaidCreate,
    service: DiceService = Depends(get_dice_service),
) -> MaidRead:
    existing = service._storage.get_maid_by_name(payload.name)  # noqa: SLF001
    if existing is not None:
        raise HTTPException(status_code=409, detail="同名骰娘已存在")
    return service.create_maid(payload.model_dump())


@maid_router.get("", response_model=list[MaidRead])
def list_maids(
    service: DiceService = Depends(get_dice_service),
) -> list[MaidRead]:
    return service.list_maids()


@maid_router.get("/{maid_id}", response_model=MaidRead)
def get_maid(
    maid_id: int,
    service: DiceService = Depends(get_dice_service),
) -> MaidRead:
    obj = service.get_maid(maid_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="骰娘不存在")
    return obj


@maid_router.put("/{maid_id}", response_model=MaidRead)
def update_maid(
    maid_id: int,
    payload: MaidUpdate,
    service: DiceService = Depends(get_dice_service),
) -> MaidRead:
    obj = service.update_maid(maid_id, payload.model_dump(exclude_unset=True))
    if obj is None:
        raise HTTPException(status_code=404, detail="骰娘不存在")
    return obj


@maid_router.delete("/{maid_id}", status_code=204)
def delete_maid(
    maid_id: int,
    service: DiceService = Depends(get_dice_service),
) -> None:
    try:
        if not service.delete_maid(maid_id):
            raise HTTPException(status_code=404, detail="骰娘不存在")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------- 掷骰 ----------------
@roll_router.post("", response_model=RollResponse, status_code=201)
def roll(
    payload: RollRequest,
    service: DiceService = Depends(get_dice_service),
) -> RollResponse:
    try:
        result = service.roll(
            payload.expression,
            maid_id=payload.maid_id,
            context=payload.context,
            note=payload.note,
            save=payload.save,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record = result["record"]
    if record is None:
        # save=False:不落库,构造一个仅用于响应的临时记录
        outcome = result["outcome"]
        record = RollRead(
            id=0,
            maid_id=payload.maid_id,
            expression=outcome.result.expression,
            total=outcome.result.total,
            details=[
                {
                    "kind": p.kind,
                    "label": p.label,
                    "value": p.value,
                    "results": p.results,
                }
                for p in outcome.result.parts
            ],
            judgement=outcome.judgement.to_dict()
            if outcome.judgement
            else None,
            context=payload.context,
            note=payload.note,
            created_at=datetime.now(),
        )
    return RollResponse(record=record, description=result["outcome"].description)


@roll_router.get("", response_model=list[RollRead])
def list_rolls(
    service: DiceService = Depends(get_dice_service),
) -> list[RollRead]:
    return service.list_rolls()


@roll_router.get("/{roll_id}", response_model=RollRead)
def get_roll(
    roll_id: int,
    service: DiceService = Depends(get_dice_service),
) -> RollRead:
    obj = service.get_roll(roll_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="掷骰记录不存在")
    return obj
