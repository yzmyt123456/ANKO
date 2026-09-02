"""本地 DND 规则库服务:查询法术/怪物/知识片段。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from anko.models import RuleKnowledge, RuleMonster, RuleSpell


class RuleService:
    """规则库查询(数据来自官方规则包 PDF 导入,存本地)。"""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def _session(self) -> Session:
        return self._sf()

    # ---------------- 统计 ----------------
    def stats(self) -> dict:
        with self._session() as s:
            spells = s.scalar(select(func.count(RuleSpell.id))) or 0
            monsters = s.scalar(select(func.count(RuleMonster.id))) or 0
            knowledge = s.scalar(select(func.count(RuleKnowledge.id))) or 0
            return {
                "spells": spells,
                "monsters": monsters,
                "knowledge": knowledge,
                "imported": spells > 0,
            }

    # ---------------- 法术 ----------------
    def search_spells(
        self, q: Optional[str] = None, limit: int = 20
    ) -> list[dict]:
        with self._session() as s:
            stmt = select(RuleSpell).order_by(RuleSpell.level, RuleSpell.name)
            if q:
                like = f"%{q}%"
                stmt = stmt.where(
                    (RuleSpell.name.like(like)) | (RuleSpell.name_en.like(like))
                )
            return [
                self._spell_dict(x)
                for x in s.execute(stmt.limit(limit)).scalars().all()
            ]

    def get_spell(self, name: str) -> Optional[dict]:
        with self._session() as s:
            obj = (
                s.execute(
                    select(RuleSpell).where(
                        (RuleSpell.name == name) | (RuleSpell.name_en == name)
                    )
                )
                .scalars()
                .first()
            )
            return self._spell_dict(obj) if obj else None

    @staticmethod
    def _spell_dict(sp: RuleSpell) -> dict:
        return {
            "id": sp.id,
            "name": sp.name,
            "name_en": sp.name_en,
            "level": sp.level,
            "school": sp.school,
            "ritual": sp.ritual,
            "casting_time": sp.casting_time,
            "range": sp.range,
            "components": sp.components,
            "duration": sp.duration,
            "description": sp.description,
        }

    # ---------------- 怪物 ----------------
    def search_monsters(
        self, q: Optional[str] = None, limit: int = 20
    ) -> list[dict]:
        with self._session() as s:
            stmt = select(RuleMonster).order_by(RuleMonster.name)
            if q:
                like = f"%{q}%"
                stmt = stmt.where(
                    (RuleMonster.name.like(like)) | (RuleMonster.name_en.like(like))
                )
            return [
                self._monster_dict(x)
                for x in s.execute(stmt.limit(limit)).scalars().all()
            ]

    def get_monster(self, name: str) -> Optional[dict]:
        with self._session() as s:
            obj = (
                s.execute(
                    select(RuleMonster).where(
                        (RuleMonster.name == name) | (RuleMonster.name_en == name)
                    )
                )
                .scalars()
                .first()
            )
            return self._monster_dict(obj) if obj else None

    @staticmethod
    def _monster_dict(m: RuleMonster) -> dict:
        return {
            "id": m.id,
            "name": m.name,
            "name_en": m.name_en,
            "meta": m.meta,
            "ac": m.ac,
            "hp": m.hp,
            "speed": m.speed,
            "abilities": m.abilities,
            "description": m.description,
        }

    # ---------------- 知识片段 ----------------
    def search_knowledge(
        self, q: str, limit: int = 10
    ) -> list[dict]:
        with self._session() as s:
            like = f"%{q}%"
            stmt = (
                select(RuleKnowledge)
                .where(RuleKnowledge.content.like(like))
                .limit(limit)
            )
            return [
                {
                    "book": x.book,
                    "page": x.page,
                    "title": x.title,
                    "content": x.content,
                }
                for x in s.execute(stmt).scalars().all()
            ]
