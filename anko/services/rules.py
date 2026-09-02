"""本地 DND 规则库服务:查询法术/怪物/知识片段。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from anko.models import RuleKnowledge, RuleMap, RuleMonster, RuleSpell


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
                "maps": s.scalar(select(func.count(RuleMap.id))) or 0,
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

    # ---------------- 地图 ----------------
    def list_maps(self, limit: int = 100) -> list[dict]:
        with self._session() as s:
            stmt = select(RuleMap).order_by(RuleMap.id).limit(limit)
            return [
                {
                    "id": m.id,
                    "name": m.name,
                    "source": m.source,
                    "file": m.file,
                    "width": m.width,
                    "height": m.height,
                }
                for m in s.execute(stmt).scalars().all()
            ]

    # ---------------- 词条本地命中 ----------------
    def resolve_term(self, name: str) -> Optional[dict]:
        """判断一个名词在本地知识库是否有收录(法术/怪物/规则)。"""
        spell = self.get_spell(name)
        if spell:
            return {
                "local": True,
                "type": "spell",
                "name": spell["name"],
                "url": f"/api/rules/spells/{spell['name']}",
            }
        monster = self.get_monster(name)
        if monster:
            return {
                "local": True,
                "type": "monster",
                "name": monster["name"],
                "url": f"/api/rules/monsters/{monster['name']}",
            }
        # 知识片段命中(标题包含该词)
        with self._session() as s:
            like = f"%{name}%"
            hit = (
                s.execute(
                    select(RuleKnowledge)
                    .where(
                        (RuleKnowledge.title.like(like))
                        | (RuleKnowledge.content.like(like))
                    )
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if hit:
                return {
                    "local": True,
                    "type": "knowledge",
                    "name": name,
                    "url": f"/api/rules/search?q={name}",
                }
        return {"local": False, "type": None, "name": name, "url": None}

    # ---------------- 知识片段 ----------------
    def list_books(self) -> list[str]:
        """知识库包含的书籍列表。"""
        with self._session() as s:
            rows = s.execute(
                select(RuleKnowledge.book)
                .distinct()
                .order_by(RuleKnowledge.book)
            ).scalars().all()
            return [b for b in rows if b]

    def list_categories(self, book: Optional[str] = None) -> list[str]:
        """知识片段分类列表(可限定书籍)。"""
        with self._session() as s:
            stmt = (
                select(RuleKnowledge.category)
                .where(RuleKnowledge.category.is_not(None))
                .distinct()
            )
            if book:
                stmt = stmt.where(RuleKnowledge.book == book)
            rows = s.execute(stmt).scalars().all()
            return [c for c in rows if c]

    def list_knowledge(
        self,
        book: Optional[str] = None,
        category: Optional[str] = None,
        kind: Optional[str] = None,
        limit: int = 60,
    ) -> list[dict]:
        """按书籍/分类列出知识片段(轻量,不含全文)。"""
        with self._session() as s:
            stmt = select(RuleKnowledge).order_by(RuleKnowledge.page, RuleKnowledge.id)
            if book:
                stmt = stmt.where(RuleKnowledge.book == book)
            if category:
                stmt = stmt.where(RuleKnowledge.category == category)
            if kind == "none":
                stmt = stmt.where(RuleKnowledge.kind.is_(None))
            elif kind:
                stmt = stmt.where(RuleKnowledge.kind == kind)
            stmt = stmt.limit(limit)
            return [
                {
                    "id": x.id,
                    "book": x.book,
                    "page": x.page,
                    "title": x.title,
                    "category": x.category,
                    "kind": x.kind,
                    "parent_id": x.parent_id,
                    "preview": (x.content or "")[:160],
                }
                for x in s.execute(stmt).scalars().all()
            ]

    def get_knowledge(self, kid: int) -> Optional[dict]:
        """单条知识片段全文(父卡附 children 子卡)。"""
        with self._session() as s:
            x = s.get(RuleKnowledge, kid)
            if x is None:
                return None
            data = {
                "id": x.id,
                "book": x.book,
                "page": x.page,
                "title": x.title,
                "category": x.category,
                "kind": x.kind,
                "parent_id": x.parent_id,
                "content": x.content,
            }
            if x.kind and x.kind != "race_part":
                kids = s.execute(
                    select(RuleKnowledge)
                    .where(RuleKnowledge.parent_id == x.id)
                    .order_by(RuleKnowledge.id)
                ).scalars().all()
                data["children"] = [
                    {
                        "id": c.id,
                        "title": c.title,
                        "page": c.page,
                        "kind": c.kind,
                        "content": c.content,
                        "book": c.book,
                    }
                    for c in kids
                ]
            return data

    def search_knowledge(
        self,
        q: str,
        limit: int = 10,
        book: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        with self._session() as s:
            like = f"%{q}%"
            stmt = select(RuleKnowledge).where(
                RuleKnowledge.content.like(like)
            )
            if book:
                stmt = stmt.where(RuleKnowledge.book == book)
            if category:
                stmt = stmt.where(RuleKnowledge.category == category)
            stmt = stmt.limit(limit)
            return [
                {
                    "id": x.id,
                    "book": x.book,
                    "page": x.page,
                    "title": x.title,
                    "category": x.category,
                    "kind": x.kind,
                    "content": x.content,
                }
                for x in s.execute(stmt).scalars().all()
            ]
