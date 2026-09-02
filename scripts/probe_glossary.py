"""探查灰机 Wiki(DND)名词页面是否存在,用于构建内置词条表。

用法: python scripts/probe_glossary.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse

# 候选词条(按类别)
CANDIDATES = {
    "属性": ["力量", "敏捷", "体质", "智力", "感知", "魅力"],
    "技能": ["运动", "体操", "巧手", "潜行", "奥秘", "历史", "调查", "自然",
             "宗教", "驯兽", "洞悉", "医疗", "察觉", "生存", "欺瞒", "威吓",
             "表演", "游说"],
    "法术(用户卡片)": ["易容术", "七彩喷射", "雷鸣波", "术法爆发", "传讯术",
                      "心灵之楔", "修复术", "次级幻象", "光亮术"],
    "常用法术": ["火球术", "魔法飞弹", "护盾术", "燃烧之手", "治愈真言",
                "睡眠术", "油腻术", "灼热射线", "闪电束", "法术反制",
                "解除魔法", "侦测魔法", "通晓语言", "隐身术", "飞行术"],
    "职业/规则": ["术士", "法师", "牧师", "战士", "盗贼", "防御等级",
                 "生命值", "熟练加值", "豁免", "施法者等级"],
    "装备/武器": ["简易武器", "矛", "匕首", "奥术法器", "皮甲", "长剑",
                 "短弓", "重弩"],
}


def probe(names: list[str]) -> dict[str, bool]:
    """用 MediaWiki API(经 curl,规避 TLS 指纹防护)检查页面是否存在。"""
    result: dict[str, bool] = {}
    for i in range(0, len(names), 40):
        batch = names[i : i + 40]
        url = (
            "https://dnd.huijiwiki.com/api.php?action=query&titles="
            + urllib.parse.quote("|".join(batch), safe="|")
            + "&format=json&redirects=1"
        )
        raw = subprocess.check_output(
            ["curl.exe", "-s", "--max-time", "25", "-A",
             "Mozilla/5.0 (anko-project)", url],
            text=True, encoding="utf-8", errors="replace",
        )
        data = json.loads(raw)
        for pid, page in data.get("query", {}).get("pages", {}).items():
            result[page.get("title", "")] = pid != "-1"
    return result


def main() -> None:
    all_names = [n for ns in CANDIDATES.values() for n in ns]
    print(f"待探查 {len(all_names)} 个词条...")
    found = probe(all_names)
    ok, missing = [], []
    for name in all_names:
        (ok if found.get(name) else missing).append(name)
    print(f"\n存在({len(ok)}):")
    for n in ok:
        print(f"  {n}")
    print(f"\n不存在({len(missing)}):")
    for n in missing:
        print(f"  {n}")


if __name__ == "__main__":
    main()
