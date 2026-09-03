# -*- coding: utf-8 -*-
"""把抓取到的楼主发言整理成可长期保留的归档:
- out/op_posts.jsonl    原始逐条(含重复楼层,页面顺序)
- out/op_unique.json    去重后(紧凑 JSON)
- 楼主发言_全档.md      人类可读全文归档(按发言时间排序)

用法: python build_archive.py
"""
from __future__ import annotations

import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
RAW = os.path.join(OUT, "op_posts.jsonl")
UNIQ = os.path.join(OUT, "op_unique.json")
MD = os.path.join(HERE, "楼主发言_全档.md")
TOPIC = "[安科/安价][MYGO][同人][DND]那么,剑与魔法,龙与地下城,女孩们的冒险开始了[过渡剧情]"
LINK = "https://ngabbs.com/read.php?tid=46321088"


def load_raw() -> list[dict]:
    rows = []
    if not os.path.exists(RAW):
        return rows
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    return rows


def norm(c: str) -> str:
    c = re.sub(r"<[^>]+>", " ", c or "")
    c = html.unescape(c)
    return re.sub(r"\s+", "", c)


def dedupe(rows: list[dict]) -> list[dict]:
    key = {}
    for p in rows:
        k = norm(p.get("content", ""))[:400]
        if not k:
            continue
        old = key.get(k)
        if old is None or p["page"] < old["page"] or (
            p["page"] == old["page"]
            and (p.get("floor", 999) if isinstance(p.get("floor"), int) else 999)
            < (old.get("floor", 999) if isinstance(old.get("floor"), int) else 999)
        ):
            key[k] = p
    return list(key.values())


def md_clean(content: str) -> str:
    c = content or ""
    # 图片:保留 alt 语义即可,不内嵌远程图
    c = re.sub(r"\[img\][^\[]*\[/img\]", "〔图〕", c, flags=re.I)
    # UBB 基础排版 → Markdown/纯文本
    c = re.sub(r"\[/?b\]", "**", c, flags=re.I)
    c = re.sub(r"\[/?i\]", "_", c, flags=re.I)
    c = re.sub(r"\[/?u\]", "_", c, flags=re.I)
    c = re.sub(r"\[size=[^\]]*\]|\[/size\]", "", c, flags=re.I)
    c = re.sub(r"\[color=[^\]]*\]|\[/color\]", "", c, flags=re.I)
    c = re.sub(r"\[/?quote\]", "\n> ", c, flags=re.I)
    c = re.sub(r"\[collapse\][^\[]*|\[/collapse\]", "", c, flags=re.I)
    c = re.sub(r"\[/?del\]", "~~", c, flags=re.I)
    # HTML 换行
    c = re.sub(r"<br\s*/?>", "\n", c, flags=re.I)
    c = re.sub(r"<[^>]+>", "", c)
    c = html.unescape(c)
    # 压缩空行(保留段落)
    c = re.sub(r"[ \t]+\n", "\n", c)
    c = re.sub(r"\n{3,}", "\n\n", c)
    return c.strip()


def fmt_floor(p: dict) -> str:
    if p.get("kind") == "floor":
        return str(p.get("floor", "?"))
    return f"首楼内嵌评论(#{p.get('comment_id', '?')})"


def build() -> None:
    rows = load_raw()
    posts = sorted(
        dedupe(rows),
        key=lambda p: (p.get("date", ""), p.get("page", 0), p.get("floor", 999) if isinstance(p.get("floor"), int) else 999),
    )
    os.makedirs(OUT, exist_ok=True)
    # 紧凑去重 JSON
    with open(UNIQ, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, separators=(",", ":"))

    chars = sum(len(p.get("content", "")) for p in posts)
    first = posts[0]["date"] if posts else "-"
    last = posts[-1]["date"] if posts else "-"
    lines = [
        f"# {TOPIC} —— 楼主发言全档",
        "",
        f"> 来源:{LINK}",
        f"> 楼主 UID 63740536 · 共 {len(posts)} 条(楼层 {sum(1 for p in posts if p.get('kind') == 'floor')} / 内嵌评论 {sum(1 for p in posts if p.get('kind') == 'comment')})",
        f"> 时间范围:{first} ~ {last} · 正文约 {chars} 字",
        f"> 由 reference_nga 爬虫读取、去重、整理;机器可读数据见 out/op_posts.jsonl 与 out/op_unique.json。",
        "",
        "---",
        "",
    ]
    for i, p in enumerate(posts, 1):
        lines.append(f"## {i}. {p.get('date', '')} · 第 {p.get('page', '?')} 页 · 楼主楼层 {fmt_floor(p)}")
        lines.append("")
        body = md_clean(p.get("content", ""))
        lines.append(body)
        lines.append("")
        lines.append("---")
        lines.append("")
    with open(MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"去重楼主发言 {len(posts)} 条;全档 {chars} 字 → {os.path.basename(MD)}")


if __name__ == "__main__":
    build()
