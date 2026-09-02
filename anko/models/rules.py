"""本地 DND 5E 规则数据模型(从官方规则包 PDF 导入,数据存本地库)。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from anko.models.base import Base


class RuleSpell(Base):
    """法术条目。"""

    __tablename__ = "rule_spells"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    level: Mapped[int] = mapped_column(Integer, default=0)
    school: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    ritual: Mapped[bool] = mapped_column(Boolean, default=False)
    casting_time: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    range: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    components: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    duration: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    description: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RuleSpell {self.name!r} lv{self.level}>"


class RuleMonster(Base):
    """怪物条目。"""

    __tablename__ = "rule_monsters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    meta: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    ac: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    hp: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    speed: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    abilities: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RuleMonster {self.name!r}>"


class RuleKnowledge(Base):
    """规则知识片段(按页/条目切块),用于检索。"""

    __tablename__ = "rule_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book: Mapped[str] = mapped_column(String(100), index=True)
    page: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    category: Mapped[Optional[str]] = mapped_column(String(50), index=True, default=None)
    content: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RuleKnowledge {self.book} p{self.page}>"


class RuleMap(Base):
    """地图素材(渲染自规则包地图 PDF)。"""

    __tablename__ = "rule_maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    file: Mapped[str] = mapped_column(String(300), nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RuleMap {self.name!r}>"
