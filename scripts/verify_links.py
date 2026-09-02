"""验证灰机 Wiki 词条页面链接有效性(含内容锚点检查)。

用法: python scripts/verify_links.py
"""

from __future__ import annotations

import json
import subprocess
import urllib.parse


def api_query(titles: str) -> dict:
    url = (
        "https://dnd.huijiwiki.com/api.php?action=query&titles="
        + urllib.parse.quote(titles, safe="|")
        + "&prop=revisions&rvprop=content&rvslots=main&format=json&redirects=1"
    )
    raw = subprocess.check_output(
        ["curl.exe", "-s", "--max-time", "25", "-A",
         "Mozilla/5.0 (anko-project)", url],
        text=True, encoding="utf-8", errors="replace",
    )
    return json.loads(raw)


def check(titles: str, anchors: tuple[str, ...] = ()) -> str:
    d = api_query(titles)
    for pid, p in d["query"]["pages"].items():
        if "missing" in p:
            return f"{titles} => MISSING"
        revs = p.get("revisions", [])
        content = revs[0]["slots"]["main"]["*"] if revs else ""
        if not content.strip():
            return f"{titles} => 空页面(无内容)"
        for a in anchors:
            if a not in content:
                return f"{titles} => 缺锚点「{a}」"
        return f"{titles} => OK ({len(content)} 字符)"
    return f"{titles} => 无结果"


if __name__ == "__main__":
    for t in [
        "玩家手册2014/属性值应用",
        "职业/2014/术士",
        "职业/2014/术士#狂野魔法",
        "术士",
        "体质",
        "易容术",
        "火球术",
    ]:
        print(check(t, ("狂野魔法",) if "狂野" in t else ()))
