# -*- coding: utf-8 -*-
"""对楼主 976 条发言做自动分类索引,并抽取决策台可复用示例。

分类:建卡实录 / 安价结算 / 剧情更新 / 规则答疑 / 公告杂谈。
输出:
  - 楼主发言_分类索引.md   按类别索引(带原文编号,可跳转楼主发言_全档.md)
  - out/posts_classified.json 每条带分类与标签
  - 决策台_示例流程.json     典型流程样例(属性骰点/意愿判定/选项掷骰等)

用法: python classify_posts.py
"""
from __future__ import annotations

import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
UNIQ = os.path.join(OUT, "op_unique.json")
INDEX_MD = os.path.join(HERE, "楼主发言_分类索引.md")
EXAMPLES_JSON = os.path.join(HERE, "决策台_示例流程.json")

CATEGORIES = ["建卡实录", "安价结算", "剧情更新", "规则答疑", "公告杂谈"]


def plain(content: str) -> str:
    c = content or ""
    c = re.sub(r"\[img\][^\[]*\[/img\]", "〔图〕", c, flags=re.I)
    c = re.sub(r"\[/?b\]|\[/?i\]|\[/?u\]|\[/?del\]", "", c, flags=re.I)
    c = re.sub(r"\[(size|color)=[^\]]*\]|\[/size\]|\[/color\]", "", c, flags=re.I)
    c = re.sub(r"\[collapse\]|\[/collapse\]|\[/?quote\]", "", c, flags=re.I)
    c = re.sub(r"<br\s*/?>", " ", c, flags=re.I)
    c = re.sub(r"<[^>]+>", "", c)
    c = html.unescape(c)
    return re.sub(r"\s+", " ", c).strip()


def classify(text: str) -> tuple[str, list[str]]:
    tags: list[str] = []
    up = text.upper()
    # —— 建卡实录 ——
    is_build = bool(
        re.search(r"1\s*D\s*16|D16|开局的各项属性|是几级的冒险者|又到了(捏人|建卡)|开始捏人|创建一位", up)
        and re.search(r"属性|等级|1D16", up)
    )
    if is_build:
        return "建卡实录", ["属性投点(取高)", "种族/职业", "背景/阵营"]

    # —— 安价/读者选项 ——
    if "安价" in text:
        sub = "结算" if ("结算" in text or "截止" in text or "结果" in text) else "征集"
        if "加权" in text:
            sub += "·加权"
        if "形象" in text or "NPC" in text:
            sub += "·NPC"
        return "安价结算", [f"安价{sub}"]

    # —— 公告/杂谈 ——
    if (re.search(r"(今天|明天|周末|今晚|下周).{0,4}(没有更新|不更新|先到这|停更|咕|连更|更新到)", text)
            or (re.search(r"感谢|抱歉|吞楼|新作|开新坑", text) and len(text) < 160)):
        return "公告杂谈", ["更新预告", "闲聊"]

    # —— 规则答疑 ——
    rule_kw = ["检定", "豁免", "DC", "AC", "调整值", "熟练", "专长", "法术位", "动作", "借机攻击", "重击", "大成功", "大失败"]
    has_rule = any(k in text for k in rule_kw)
    askish = bool(re.search(r"[?？]|怎么|为什么|吗|对吧|是不是|要不要", text))
    if has_rule and askish and len(text) < 900:
        return "规则答疑", ["规则解释", "判定说明"]

    # —— 剧情更新(默认主体) ——
    has_dice = bool(re.search(r"\[\s*\d*\s*D\s*\d|1D\d", up))
    return "剧情更新", (["掷骰驱动"] if has_dice else ["叙述推进"])


def snippets(text: str, n: int = 64) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"



def main() -> None:
    posts = json.load(open(UNIQ, encoding="utf-8"))
    posts.sort(
        key=lambda p: (
            p.get("date", ""),
            p.get("page", 0),
            p.get("floor", 999) if isinstance(p.get("floor"), int) else 999,
        )
    )
    anno = []
    for i, p in enumerate(posts, 1):
        cat, tags = classify(plain(p.get("content", "")))
        anno.append({
            "archive_no": i,
            "date": p.get("date", ""),
            "page": p.get("page"),
            "floor": p.get("floor"),
            "kind": p.get("kind"),
            "category": cat,
            "tags": tags,
        })
    json.dump(
        anno,
        open(os.path.join(OUT, "post_annotations.json"), "w", encoding="utf-8"),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    lines = [
        "# 楼主发言分类索引(tid 46321088)",
        "",
        f"> 共 {len(anno)} 条 · 分类:{' / '.join(CATEGORIES)} · 各条对应《楼主发言_全档.md》中的编号。",
        "",
    ]
    counts = {c: 0 for c in CATEGORIES}
    for cat in CATEGORIES:
        group = [p for p in anno if p["category"] == cat]
        counts[cat] = len(group)
        lines += [f"## {cat}({len(group)})", "", "| 编号 | 时间 | 页·楼 | 标签 | 内容摘要 |", "|---|---|---|---|---|"]
        for p in group:
            floor = p.get("floor", "评论") if isinstance(p.get("floor"), int) else "评论"
            tags = "、".join(p.get("tags", []) or [])
            lines.append(
                f"| {p['archive_no']} | {p.get('date','')} | {p.get('page','?')}页·{floor}楼 | {tags} | {snippets(plain(p.get('content','')))} |"
            )
        lines.append("")
    lines.append("---\n")
    lines.append("分类分布:" + ", ".join(f"{k}={v}" for k, v in counts.items()))
    open(INDEX_MD, "w", encoding="utf-8").write("\n".join(lines))

    # —— 决策台示例:从真实发言抽几段典型流程 ——
    def first(pred):
        return next((p for p in posts if pred(plain(p.get("content", "")))), None)

    attr = first(lambda t: "1D16" in t.upper() and "属性" in t)
    wish = first(lambda t: "愿意" in t and "1D" in t.upper() and "70" in t)
    check = first(lambda t: "检定" in t and "DC" in t and "1D20" in t.upper())
    multi = first(lambda t: "4D20" in t.upper() and "戏法" in t)

    examples = [
        {
            "kind": "建卡·属性骰点",
            "name": "六维属性:两次 1d16+2 取高",
            "source": {"date": attr.get("date"), "page": attr.get("page"), "floor": attr.get("floor")} if attr else None,
            "desc": "六项属性分别掷两次 1d16+2,取数值高的一次作为结果(普通人约 10)。",
            "expr": "1d16+2", "rolls": 2, "select": "取高",
        },
        {
            "kind": "意愿/态度",
            "name": "d100 意愿 + 修正 + 档位",
            "source": {"date": wish.get("date"), "page": wish.get("page"), "floor": wish.get("floor")} if wish else None,
            "desc": "判定角色是否愿意加入/参与:投 d100,先给修正(如好朋友 +30),再按 50/70 档位定性。",
            "expr": "1d70+30",
            "thresholds": ["50以上:愿意参与眼前的事", "70以上:愿意同行/接受请求"],
        },
        {
            "kind": "检定",
            "name": "D20 检定 vs DC",
            "source": {"date": check.get("date"), "page": check.get("page"), "floor": check.get("floor")} if check else None,
            "desc": "战斗/技能判定:1d20 + 调整值与熟练,对比 DC(如简单 DC10)判定成败。",
            "expr": "1d20+7", "thresholds": ["15以上:完全成功", "10以上:部分成功"],
        },
        {
            "kind": "建卡·法术/技能列表",
            "name": "从列表批量抽选(重复补抽)",
            "source": {"date": multi.get("date"), "page": multi.get("page"), "floor": multi.get("floor")} if multi else None,
            "desc": "一次性掷多个 d20 从戏法/技能表抽项;掷到重复项时再补抽。",
            "expr": "4d20", "rule": "命中后按列表编号展开;重复项 1d20 补抽",
        },
    ]
    json.dump(examples, open(EXAMPLES_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("分类完成:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    print("示例流程:", len(examples), "条 →", os.path.basename(EXAMPLES_JSON))


if __name__ == "__main__":
    main()
