"""楼主语料本地向量检索(零依赖版)。

- 数据源:reference_nga/out/op_unique.json(正文) + post_annotations.json(分类)
- 向量:中文 2-gram + 局部 1-gram 的稀疏哈希向量,余弦相似度排序。
  属于"本地 n-gram 向量检索",无需任何外部 embedding 模型即可离线运行;
  未来接入 OpenAI 兼容 embeddings 时可在此模块替换后端。
"""
from __future__ import annotations

import html
import json
import re
import zlib
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "reference_nga" / "out"
HASH_DIM = 4096


def _plain(content: str) -> str:
    c = content or ""
    c = re.sub(r"\[img\][^\[]*\[/img\]", "〔图〕", c, flags=re.I)
    c = re.sub(r"\[/?b\]|\[/?i\]|\[/?u\]|\[/?del\]", "", c, flags=re.I)
    c = re.sub(r"\[(size|color)=[^\]]*\]|\[/size\]|\[/color\]", "", c, flags=re.I)
    c = re.sub(r"\[collapse\]|\[/collapse\]|\[/?quote\]", "", c, flags=re.I)
    c = re.sub(r"<br\s*/?>", " ", c, flags=re.I)
    c = re.sub(r"<[^>]+>", "", c)
    c = html.unescape(c)
    return re.sub(r"\s+", "", c)


def _grams(text: str) -> list[str]:
    out: list[str] = []
    if not text:
        return out
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            out.append(ch)
    bigrams = [text[i:i + 2] for i in range(len(text) - 1)]
    return bigrams + out


def _vec(text: str) -> dict[int, float]:
    counts: dict[int, int] = {}
    for g in _grams(text):
        if not g:
            continue
        idx = zlib.crc32(g.encode("utf-8")) % HASH_DIM
        counts[idx] = counts.get(idx, 0) + 1
    return {k: 1.0 + (v - 1) * 0.5 for k, v in counts.items()}  # 轻度压缩高频


def _cos(a: dict[int, float], b: dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = 0.0
    na = nb = 0.0
    for k, v in a.items():
        na += v * v
        bv = b.get(k)
        if bv:
            dot += v * bv
    for v in b.values():
        nb += v * v
    if not dot or not na or not nb:
        return 0.0
    return dot / ((na * nb) ** 0.5)


class _CorpusIndex:
    def __init__(self) -> None:
        self._docs: list[dict] | None = None

    def _load(self) -> list[dict]:
        if self._docs is not None:
            return self._docs
        docs: list[dict] = []
        posts_fp = DATA_DIR / "op_unique.json"
        anno_fp = DATA_DIR / "post_annotations.json"
        if posts_fp.exists() and anno_fp.exists():
            posts = json.loads(posts_fp.read_text(encoding="utf-8"))
            anno = json.loads(anno_fp.read_text(encoding="utf-8"))
            by_no = {str(a.get("archive_no")): a for a in anno}
            for i, p in enumerate(posts, 1):
                meta = by_no.get(str(i), {})
                text = _plain(p.get("content", ""))
                if not text or len(text) < 30:
                    continue
                docs.append({
                    "text": text,
                    "date": p.get("date", ""),
                    "page": p.get("page"),
                    "floor": p.get("floor"),
                    "category": meta.get("category", ""),
                    "tags": meta.get("tags", []),
                    "vec": _vec(text),
                })
        self._docs = docs
        return docs

    def search(
        self,
        query: str,
        top: int = 3,
        prefer_category: str = "",
    ) -> list[dict]:
        q = _plain(query)
        if not q:
            return []
        qv = _vec(q)
        scored: list[tuple[float, dict]] = []
        for d in self._load():
            score = _cos(qv, d["vec"])
            if prefer_category and d["category"] == prefer_category:
                score += 0.12
            if score > 0.015:
                scored.append((score, d))
        scored.sort(key=lambda x: -x[0])
        out = []
        for _, d in scored[:top]:
            snippet = d["text"][:260]
            out.append({
                "date": d["date"],
                "page": d["page"],
                "floor": d["floor"],
                "category": d["category"],
                "tags": d["tags"],
                "snippet": snippet,
            })
        return out

    def count(self) -> int:
        return len(self._load())


_index = _CorpusIndex()


def search_corpus(
    query: str,
    top: int = 3,
    prefer_category: str = "",
) -> list[dict]:
    return _index.search(query, top=top, prefer_category=prefer_category)


def corpus_stats() -> dict:
    return {"docs": _index.count(), "dim": HASH_DIM}


def format_corpus_refs(refs: list[dict]) -> str:
    if not refs:
        return ""
    parts = []
    for i, r in enumerate(refs, 1):
        where = f"{r.get('date','')} p{r.get('page','?')}·{r.get('floor','')}楼"
        parts.append(
            f"[参考{i} · {r.get('category','')} · {where}]\n"
            f"{r['snippet']}\n"
            "(仅借鉴这段的节奏/规则/叙事手法,不要原文复述)"
        )
    return "\n\n".join(parts)
