"""知识库本地向量检索(DM 调动知识库用)。

与 corpus.py 相同的 n-gram 向量方案,把玩家手册等知识片段做成索引;
导游在 DM 提案 / 续写时按“当前正文+角色+倾向”取 Top-N 规则参考注入提示词。
"""
from __future__ import annotations

import html
import re
import zlib

from anko.services.rules import RuleService

HASH_DIM = 4096


def _plain(content: str) -> str:
    c = content or ""
    c = re.sub(r"<[^>]+>", " ", c)
    c = html.unescape(c)
    return re.sub(r"\s+", "", c).strip()


def _vec(text: str) -> dict[int, float]:
    t = _plain(text)
    grams: list[str] = []
    for ch in t:
        if "\u4e00" <= ch <= "\u9fff":
            grams.append(ch)
    grams += [t[i:i + 2] for i in range(len(t) - 1)]
    counts: dict[int, int] = {}
    for g in grams:
        idx = zlib.crc32(g.encode("utf-8")) % HASH_DIM
        counts[idx] = counts.get(idx, 0) + 1
    return {k: 1.0 + (v - 1) * 0.5 for k, v in counts.items()}


def _cos(a: dict[int, float], b: dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = na = nb = 0.0
    for k, v in a.items():
        na += v * v
        bv = b.get(k)
        if bv:
            dot += v * bv
    for v in b.values():
        nb += v * v
    return dot / ((na * nb) ** 0.5) if (dot and na and nb) else 0.0


class KnowledgeRag:
    """按需懒加载的知识库索引;同一 app 实例内缓存。"""

    def __init__(self, rule_service: RuleService) -> None:
        self._svc = rule_service
        self._docs: list[dict] | None = None

    def _load(self) -> list[dict]:
        if self._docs is not None:
            return self._docs
        docs: list[dict] = []
        try:
            rows = self._svc.list_all_knowledge(limit=5000)
        except Exception:  # noqa: BLE001 知识库缺失不阻断
            rows = []
        for r in rows:
            text = f"{r.get('title', '')} {r.get('content', '')}"
            t = _plain(text)
            if len(t) < 30:
                continue
            docs.append({
                "title": r.get("title", ""),
                "book": r.get("book", ""),
                "page": r.get("page"),
                "category": r.get("category", ""),
                "kind": r.get("kind", ""),
                "snippet": t[:420],
                "vec": _vec(text),
            })
        self._docs = docs
        return docs

    def search(self, query: str, top: int = 4) -> list[dict]:
        q = _plain(query)
        if not q:
            return []
        qv = _vec(q)
        scored: list[tuple[float, dict]] = []
        for d in self._load():
            score = _cos(qv, d["vec"])
            if score > 0.02:
                scored.append((score, d))
        scored.sort(key=lambda x: -x[0])
        return [d for _, d in scored[:top]]

    def count(self) -> int:
        return len(self._load())


def format_refs(refs: list[dict]) -> str:
    if not refs:
        return ""
    parts = []
    for r in refs:
        loc = f"{r['book'] or '规则'} p{r.get('page', '?')}"
        parts.append(f"[知识库·{r.get('title', '')[:30]} · {loc}]\n{r['snippet']}")
    return "\n\n".join(parts)


def retrieve_and_format(rag: KnowledgeRag, query: str, top: int = 4) -> str:
    try:
        refs = rag.search(query, top=top)
        return format_refs(refs)
    except Exception:  # noqa: BLE001
        return ""
