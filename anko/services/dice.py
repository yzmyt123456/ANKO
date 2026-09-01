"""骰娘与掷骰业务服务。"""

from __future__ import annotations

from typing import Any, Optional

from anko.core.interfaces import Storage
from anko.dice.engine import DiceEngine, RollOutcome
from anko.dice.maids import MaidConfig, default_maid_data


class DiceService:
    """骰娘管理 + 执行掷骰并落库。"""

    def __init__(
        self,
        storage: Storage,
        engine: DiceEngine,
        default_maid_name: str = "命运之骰",
    ) -> None:
        self._storage = storage
        self._engine = engine
        self._default_maid_name = default_maid_name

    # ---------- 骰娘管理 ----------
    def ensure_default_maid(self) -> Any:
        """确保内置骰娘存在(首次启动时调用)。"""
        existing = self._storage.get_maid_by_name(self._default_maid_name)
        if existing is None:
            return self._storage.create_maid(
                default_maid_data(self._default_maid_name)
            )
        return existing

    def list_maids(self, *, offset: int = 0, limit: int = 100) -> list[Any]:
        return self._storage.list_maids(offset=offset, limit=limit)

    def get_maid(self, maid_id: int) -> Optional[Any]:
        return self._storage.get_maid(maid_id)

    def get_maid_config(self, maid_id: int) -> Optional[MaidConfig]:
        model = self._storage.get_maid(maid_id)
        return MaidConfig.from_model(model) if model else None

    def create_maid(self, data: dict) -> Any:
        """创建一个自定义骰娘。"""
        payload = {
            "name": data["name"],
            "personality": data.get("personality"),
            "greeting": data.get("greeting"),
            "default_expression": data.get("default_expression") or "1d100",
            "settings": data.get("settings") or {},
            "is_system": False,
            "extra": data.get("extra") or {},
        }
        return self._storage.create_maid(payload)

    def update_maid(self, maid_id: int, data: dict) -> Optional[Any]:
        payload = {
            k: v
            for k, v in data.items()
            if k
            in {
                "name",
                "personality",
                "greeting",
                "default_expression",
                "settings",
                "extra",
            }
        }
        if not payload:
            return self._storage.get_maid(maid_id)
        return self._storage.update_maid(maid_id, payload)

    def delete_maid(self, maid_id: int) -> bool:
        model = self._storage.get_maid(maid_id)
        if model is None:
            return False
        if model.is_system:
            raise ValueError("系统内置骰娘不可删除")
        return self._storage.delete_maid(maid_id)

    # ---------- 掷骰记录 ----------
    def list_rolls(self, *, offset: int = 0, limit: int = 100) -> list[Any]:
        return self._storage.list_rolls(offset=offset, limit=limit)

    def get_roll(self, roll_id: int) -> Optional[Any]:
        return self._storage.get_roll(roll_id)

    # ---------- 掷骰 ----------
    def roll(
        self,
        expression: Optional[str] = None,
        *,
        maid_id: Optional[int] = None,
        context: Optional[dict] = None,
        note: Optional[str] = None,
        save: bool = True,
    ) -> dict:
        """执行掷骰,返回 {"record", "outcome"}。

        save=False 时不落库,record 为 None。
        """
        if maid_id is not None:
            maid_model = self._storage.get_maid(maid_id)
            if maid_model is None:
                raise KeyError(f"骰娘不存在:{maid_id}")
            maid = MaidConfig.from_model(maid_model)
        else:
            default = self.ensure_default_maid()
            maid = MaidConfig.from_model(default)

        expression = (expression or "").strip() or maid.default_expression
        outcome: RollOutcome = self._engine.roll(expression, maid=maid)

        record = None
        if save:
            record = self._storage.create_roll(
                {
                    "maid_id": maid.id,
                    "expression": outcome.result.expression,
                    "total": outcome.result.total,
                    "details": [
                        {
                            "kind": p.kind,
                            "label": p.label,
                            "value": p.value,
                            "results": p.results,
                        }
                        for p in outcome.result.parts
                    ],
                    "judgement": outcome.judgement.to_dict()
                    if outcome.judgement
                    else None,
                    "context": context or {},
                    "note": note,
                }
            )
        return {"record": record, "outcome": outcome}

