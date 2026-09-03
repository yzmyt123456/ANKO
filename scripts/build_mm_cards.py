# -*- coding: utf-8 -*-
"""怪物图鉴 → 图文知识卡(视觉切图)。

方法(与城主指南同一套布局阅读):
1. 统计块“名称行”判定:某行下方紧邻“体型类型”meta 行 → 该行是怪物名(绕过右栏 lore 大标题);
2. 正文按两栏阅读顺序重组并分段;
3. 同一页内自动把插图 bbox 裁成 PNG,挂到最近/对应怪物的知识卡 image;
4. 输出 RuleKnowledge(kind='monster', category='怪物资料'),先清旧 book。

用法: python scripts/build_mm_cards.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pymupdf

import build_dmg_cards as B

MM_PDF = Path("D:/bdxiazi/DND 5E 规则包/DND_5E_怪物图鉴CN.pdf")
BOOK = "DND_5E_怪物图鉴CN"
IMG_DIR = Path("anko/static/img/kb/monsters")
META_RE = re.compile(r"^(微型|小型|中型|大型|超大型|巨型)[^,，]{0,16}[,，]")


def is_monster_anchor(lines: list[dict], idx: int, mid: float) -> bool:
    """统计块起点(只在本栏内检查):名称行 → 体型meta → AC/HP/速度。"""
    if idx >= len(lines) - 2:
        return False
    if lines[idx]["size"] < 13:
        return False
    col = 0 if lines[idx]["x"] < mid else 1

    def same_col(ln: dict) -> bool:
        return (0 if ln["x"] < mid else 1) == col

    nxt = next((ln for ln in lines[idx + 1: idx + 6] if same_col(ln)), None)
    if nxt is None or not (nxt["y"] - lines[idx]["y"] < 40 and bool(META_RE.search(nxt["text"]))):
        return False
    tail = [ln for ln in lines[idx + 1: idx + 14] if same_col(ln)]
    keys = ["AC", "HP", "速度"]
    ki = 0
    for ln in tail:
        t = ln["text"].lstrip()
        if ki == 0 and t.startswith("AC"):
            ki = 1
            continue
        if ki == 1 and t.startswith("HP"):
            ki = 2
            continue
        if ki == 2 and t.startswith("速度"):
            return True
    return False


def build_cards() -> list[dict]:
    doc = pymupdf.open(MM_PDF)
    cards: list[dict] = []
    cur: dict | None = None
    seq = 0

    def flush() -> None:
        nonlocal cur
        if cur and cur["content"].strip():
            cards.append(cur)
        cur = None

    # 页脚印刷页码(Y>790 的纯数字)
    last_printed = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        raw_head = page.get_text("text")[:220].replace("\n", " ")
        if ("目录" in raw_head and "Contents" in raw_head) or ("索引" in raw_head and "Index" in raw_head):
            continue
        all_lines = B.page_lines(page)
        printed = None
        body = []
        for ln in all_lines:
            if ln["y"] > 790 and re.fullmatch(r"\d{1,3}", ln["text"]):
                printed = int(ln["text"])
            else:
                body.append(ln)
        if printed:
            last_printed = printed
        else:
            printed = last_printed + 1 if last_printed else (pno + 1)

        mid = page.rect.width / 2
        # 统计块名称锚点(同一页内可能多个怪物)
        anchors: list[dict] = []
        for i, ln in enumerate(body):
            if is_monster_anchor(body, i, mid) and not any(
                a["y"] == ln["y"] for a in anchors
            ):
                anchors.append({"y": ln["y"], "text": B.clean_title(ln["text"])})
        anchors.sort(key=lambda a: a["y"])

        if anchors and cur is not None:
            flush()  # 上一只怪物到此页为止(跨页尾巴允许少量丢失,保证按名成卡)

        # 正文阅读顺序(两栏)
        mid = page.rect.width / 2
        left = sorted([ln for ln in body if ln["x"] < mid], key=lambda a: a["y"])
        right = sorted([ln for ln in body if ln["x"] >= mid], key=lambda a: a["y"])
        items = [{"text": ln["text"], "y": ln["y"], "x": ln["x"]} for ln in left + right]

        used = [False] * len(anchors)
        last_y: float | None = None
        for it in items:
            txt = B.clean_title(it["text"])
            rn = re.sub(r"\s+", "", txt)
            if not rn:
                continue
            hit = None
            for i, a in enumerate(anchors):
                if used[i]:
                    continue
                an = re.sub(r"\s+", "", a["text"])
                if an == rn or (len(an) >= 2 and an in rn) or (len(rn) >= 2 and rn in an):
                    hit = i
                    break
            if hit is not None:
                used[hit] = True
                flush()
                seq += 1
                cur = {
                    "title": anchors[hit]["text"],
                    "page": printed,
                    "content": "",
                    "anchor_y": anchors[hit]["y"],
                    "pno": pno,
                }
                last_y = None
                continue
            if cur is None:
                continue
            if not cur["content"]:
                cur["content"] = txt
            elif last_y is not None and abs(it["y"] - last_y) < 16.5:
                pc, nc = cur["content"][-1], txt[:1]
                sep = " " if (pc.isascii() and pc.isalnum() and nc.isascii() and nc.isalnum()) else ""
                cur["content"] += sep + txt
            else:
                cur["content"] += "\n" + txt
            last_y = it["y"]
    flush()
    return cards


def main() -> None:
    write = "--write" in sys.argv
    doc = pymupdf.open(MM_PDF)
    cards = build_cards()
    print("识别怪物统计块:", len(cards))
    for c in cards[:8]:
        print(f"- p{c['page']} | {c['title']} | 正文{len(c['content'])}字")
    if not write:
        print("(预览模式,加 --write 才写入图片与知识库)")
        return

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    for f in IMG_DIR.glob("mm_cn_*"):
        f.unlink()  # 重新生成,避免旧命名残留
    # 给每只怪物配图:同页插图按 y 就近分配
    page_images: dict[int, list[dict]] = {}
    for pno in range(doc.page_count):
        try:
            infos = [x for x in doc[pno].get_image_info() if x.get("bbox")]
        except Exception:  # noqa: BLE001
            continue
        # 本页文本行(用于衡量“图内文字量”)
        spans: list[tuple[float, float, float, float, int]] = []
        try:
            for b in doc[pno].get_text("dict")["blocks"]:
                for l in b.get("lines", []):
                    spans.append((l["bbox"][0], l["bbox"][1], l["bbox"][2], l["bbox"][3], sum(len(s["text"]) for s in l.get("spans", []))))
        except Exception:  # noqa: BLE001
            spans = []
        pg_area = doc[pno].rect.width * doc[pno].rect.height
        big = []
        for x in infos:
            x0, y0, x1, y1 = x["bbox"]
            if (x1 - x0) >= 90 and (y1 - y0) >= 80:
                area = (x1 - x0) * (y1 - y0)
                # 图内文字重叠量
                inner = 0
                for sx0, sy0, sx1, sy1, n in spans:
                    if sx1 >= x0 and sx0 <= x1 and sy1 >= y0 and sy0 <= y1:
                        inner += n
                big.append({
                    "bbox": x["bbox"], "cy": (y0 + y1) / 2, "top": y0,
                    "area": area, "pg_area": pg_area, "text": inner,
                })
        if big:
            page_images[pno] = big

    conn = sqlite3.connect("data/anko.db")
    cur_db = conn.cursor()
    old = cur_db.execute("select count(*) from rule_knowledge where book=?", (BOOK,)).fetchone()[0]
    cur_db.execute("delete from rule_knowledge where book=?", (BOOK,))

    # 每页候选按“图内文字量”升序:最“干净”(几乎无文字)的图当怪物立绘,次干净或顶部横幅当介绍图
    def _page_pool(pno: int) -> list[dict]:
        pool0 = page_images.get(pno) or []
        pool = [x for x in pool0 if x["area"] < 0.72 * x["pg_area"]]
        return sorted(pool or pool0, key=lambda x: (x["text"], x["top"]))

    side_of_page: dict[int, dict] = {}
    for pno, cands in page_images.items():
        pool = _page_pool(pno)
        if len(pool) >= 2:
            by_top = sorted(pool, key=lambda x: x["top"])
            a, b = by_top[0], by_top[1]
            if b["top"] - a["top"] >= 120:
                # 上方的图通常是介绍/横幅,下方留给怪物立绘
                side_of_page[pno] = a
            else:
                # 两张同排:把“最干净”留给怪物,另一张当介绍
                side_of_page[pno] = pool[1] if pool[0]["text"] < pool[1]["text"] else pool[0]
    rows = []
    used: dict[int, list[dict]] = {}
    side_done: set[int] = set()

    def crop_to(cand: dict, fname: str) -> str:
        b = cand["bbox"]
        pix = doc[pno].get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(b))
        from io import BytesIO
        from PIL import Image as PILImage
        img = PILImage.open(BytesIO(pix.tobytes("png"))).convert("RGB")
        img.save(IMG_DIR / fname, quality=82, optimize=True)
        return f"/static/img/kb/monsters/{fname}"

    for i, c in enumerate(cards):
        pno = c.get("pno", 0)
        pool = _page_pool(pno)
        side = side_of_page.get(pno)
        used_now = used.setdefault(pno, [])
        # 最干净的可用图优先给怪物
        avail = [x for x in pool if x not in used_now and x is not side]
        best = avail[0] if avail else (next((x for x in pool if x not in used_now), None))
        img_path = None
        if best is not None:
            used_now.append(best)
            img_path = crop_to(best, f"mm_cn_{i:04d}_monster.jpg")
        side_path = None
        if side is not None and pno not in side_done and side not in used_now:
            side_done.add(pno)
            side_path = crop_to(side, f"mm_cn_{i:04d}_intro.jpg")
        rows.append((
            BOOK, c["page"], c["title"][:200], "怪物资料", "monster",
            c["content"][:12000], img_path, side_path,
        ))

    cur_db.executemany(
        "insert into rule_knowledge (book,page,title,category,kind,content,image,image_side) "
        "values (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    monsters = sum(1 for r in rows if r[6])
    intros = sum(1 for r in rows if r[7])
    print(f"已替换:旧卡 {old} → 新怪物图文卡 {len(rows)}(怪物图 {monsters} + 介绍图 {intros})")


if __name__ == "__main__":
    main()
