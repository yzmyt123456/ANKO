# -*- coding: utf-8 -*-
"""用布局感知把《城主指南》重切成知识卡(先校准,带 --write 才入库)。

方法:
1. PyMuPDF 逐页取词(含字号/坐标),两栏排版按 dict 顺序自然还原;
2. 页脚数字(y>790)识别为印刷页码;
3. 标题识别:size>=14.5 为“章/大节”,size>=11.5 且短行为“子节”,二者都作为卡边界;
4. 每张卡:标题(中文+英文)+正文段落,记录起止印刷页;
5. --write 时清空 book='DND_5E_城主指南CN' 旧卡并写入(事务)。
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

import pymupdf

PDF = Path("D:/bdxiazi/DND 5E 规则包/DND_5E_城主指南CN.pdf")
BOOK = "DND_5E_城主指南CN"
BIG = 14.5
SUB = 11.5


def page_lines(page) -> list[dict]:
    d = page.get_text("dict")
    lines: list[dict] = []
    for block in d.get("blocks", []):
        for ln in block.get("lines", []):
            spans = [s for s in ln.get("spans", []) if s.get("text", "").strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans).strip()
            if not text:
                continue
            size = max(s["size"] for s in spans)
            bold = any(s.get("flags", 0) & 16 for s in spans)
            lines.append({
                "x": min(s["bbox"][0] for s in spans),
                "y": ln["bbox"][1],
                "size": size,
                "bold": bold,
                "text": text,
            })
    lines.sort(key=lambda a: (round(a["y"], 1), a["x"]))
    return lines


def clean_title(t: str) -> str:
    t = re.sub(r"\\x00", "", t)
    return re.sub(r"\s+", " ", t).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    doc = pymupdf.open(PDF)
    cards: list[dict] = []
    cur: dict | None = None
    last_printed = 0

    def flush() -> None:
        nonlocal cur
        if cur and (cur["content"].strip() or not cards):
            cards.append(cur)
        cur = None

    for pno in range(doc.page_count):
        page = doc[pno]
        raw_text = page.get_text("text")
        head = raw_text[:220].replace("\n", " ")
        # 跳过目录与索引整页,避免把 TOC 条目当标题
        if ("目录" in head and "Contents" in head) or ("索引" in head and "Index" in head):
            continue
        lines = page_lines(page)
        # 页脚:纯数字且在页面底部 = 印刷页码
        printed = None
        body_lines = []
        for ln in lines:
            if ln["y"] > 790 and re.fullmatch(r"\d{1,3}", ln["text"]):
                printed = int(ln["text"])
            else:
                body_lines.append(ln)
        if printed:
            last_printed = printed
        else:
            printed = last_printed + 1 if last_printed else (pno + 1)

        # 本页标题锚(按字号检测;尺寸越大的越优先匹配)
        anchors: list[dict] = []
        for ln in body_lines:
            t = clean_title(ln["text"])
            sz = ln["size"]
            if (sz >= BIG or (sz >= SUB and len(t) <= 48)) and sz >= 11.5:
                anchors.append({"norm": re.sub(r"\s+", "", t), "raw": t, "y": ln["y"], "sz": sz})
        anchors.sort(key=lambda a: a["y"])

        # 正文阅读顺序:普通页按“左栏→右栏”;含跨栏表格的页退回 sort=True(行序优先)
        def page_items() -> list[dict]:
            try:
                tabs = page.find_tables()
                wide = [t for t in tabs.tables if (t.bbox[2] - t.bbox[0]) > page.rect.width * 0.55]
                if len(wide) >= 3:
                    raw = [clean_title(x) for x in page.get_text("text", sort=True).splitlines()]
                    raw = [x for x in raw if x]
                    while raw and raw[-1].isdigit() and len(raw[-1]) <= 3:
                        raw.pop()
                    return [{"text": x, "y": None} for x in raw]
            except Exception:  # noqa: BLE001 表检测失败就按两栏处理
                pass
            mid = page.rect.width / 2
            left = sorted([ln for ln in body_lines if ln["x"] < mid], key=lambda a: a["y"])
            right = sorted([ln for ln in body_lines if ln["x"] >= mid], key=lambda a: a["y"])
            return [{"text": ln["text"], "y": ln["y"]} for ln in left + right]

        items = page_items()
        used = [False] * len(anchors)
        _last_y: float | None = None

        def append_paragraph(cur: dict, text: str, y: float | None) -> None:
            nonlocal _last_y
            if not cur["content"]:
                cur["content"] = text
            elif y is not None and _last_y is not None and abs(y - _last_y) < 18:
                # 同一段落内的折行:直接续接(中英之间补空格)
                prev_ch = cur["content"][-1]
                next_ch = text[:1]
                sep = " " if (prev_ch.isascii() and prev_ch.isalnum() and next_ch.isascii() and next_ch.isalnum()) else ""
                cur["content"] += sep + text
            else:
                cur["content"] += "\n" + text
            if y is not None:
                _last_y = y

        for item in items:
            rline = item["text"]
            y = item["y"]
            rn = re.sub(r"\s+", "", rline)
            if not rn or (rn.isdigit() and len(rn) <= 3):
                continue
            hit = None
            for i, a in enumerate(anchors):
                if used[i] or not a["norm"]:
                    continue
                if rn == a["norm"] or (len(a["norm"]) >= 2 and a["norm"] in rn) or (len(rn) >= 2 and rn in a["norm"]):
                    hit = i
                    break
            if hit is not None:
                used[hit] = True
                flush()
                cur = {"title": rline, "size": round(anchors[hit]["sz"], 1), "page": printed, "content": ""}
                _last_y = None
                continue
            if cur is None:
                cur = {"title": f"(无标题 p{printed})", "size": 0, "page": printed, "content": ""}
                _last_y = None
            append_paragraph(cur, rline, y)
    flush()

    # 跳过封面/目录产生的散卡:从印刷第 6 页(第1章)才开始正文
    cards = [c for c in cards if c["page"] >= 6]

    # 剔除“第?部分”分隔页(内容基本为空或仅导语)
    def is_part(c: dict) -> bool:
        return bool(re.match(r"^第\s*[一二三四五六七八九十\d]+\s*部分", c["title"])) and len(c["content"]) < 1500

    cards = [c for c in cards if not is_part(c)]

    # 回并英文折行标题(如 "绘制战役Mapping Your" + "Campaign")
    merged: list[dict] = []
    for c in cards:
        if (
            merged
            and c["title"].isascii()
            and len(c["title"]) <= 30
            and len(merged[-1].get("content", "")) <= 60
        ):
            merged[-1]["title"] = clean_title(merged[-1]["title"] + " " + c["title"])
            if c["content"]:
                merged[-1]["content"] += (("\n" if merged[-1]["content"] else "") + c["content"])
            continue
        merged.append(c)
    cards = merged

    # 给卡补章节分类
    chapter = ""
    chapter_no = 0
    cn_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    for c in cards:
        m = re.match(r"^第\s*([一二三四五六七八九十\d]+)\s*章", c["title"])
        if m and c["size"] >= 16:
            token = m.group(1)
            chapter_no = cn_nums.get(token, int(token) if token.isdigit() else chapter_no)
            chapter = f"第{token}章"
            c["category"] = chapter
            continue
        c["category"] = chapter or ""
    out = Path("data/dmg_cards_probe.json")
    out.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    print("有效知识卡:", len(cards), "总字数:", sum(len(c["content"]) for c in cards))
    cats = {}
    for c in cards:
        cats[c["category"]] = cats.get(c["category"], 0) + 1
    print("章节分布:", dict(sorted(cats.items(), key=lambda x: -x[1])))

    if args.write:
        conn = sqlite3.connect("data/anko.db")
        cur = conn.cursor()
        old = cur.execute("select count(*) from rule_knowledge where book=?", (BOOK,)).fetchone()[0]
        cur.execute("delete from rule_knowledge where book=?", (BOOK,))
        rows = []
        for c in cards:
            rows.append((
                BOOK, c["page"], c["title"][:200], c.get("category") or None, None,
                c["content"].strip(), None,
            ))
        cur.executemany(
            "insert into rule_knowledge (book,page,title,category,kind,content,parent_id) values (?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
        conn.close()
        print(f"已重写:删除旧卡 {old} 条 → 写入新卡 {len(rows)} 条")


if __name__ == "__main__":
    main()
