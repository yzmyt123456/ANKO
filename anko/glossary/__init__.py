"""DND 专有名词词典。

内置词条与对应灰机 Wiki 释义页链接,供人物卡 / 剧情中的专有名词
一键跳转。词条来源:https://dnd.huijiwiki.com(玩家手册 2024)。
"""

from anko.glossary.registry import (
    DND_WIKI_BASE,
    GlossaryEntry,
    find_entries,
    linkify,
    list_entries,
)

__all__ = [
    "DND_WIKI_BASE",
    "GlossaryEntry",
    "list_entries",
    "find_entries",
    "linkify",
]
