"""真实调用 DeepSeek 验证生成角色的过程文本格式(消耗少量 API 配额)。

用法: python scripts/try_generate.py
"""

from __future__ import annotations

import httpx

B = "http://127.0.0.1:8000"


def main() -> None:
    buffer = ""
    done: dict | None = None
    with httpx.stream(
        "POST",
        f"{B}/api/ai/generate-character/stream",
        json={
            "template": "dnd5e",
            "story_context": "剑与魔法的费伦大陆,一场新的冒险即将开始。",
            "hint": "",
        },
        timeout=150,
    ) as r:
        print("STATUS:", r.status_code)
        for line in r.iter_lines():
            if not line.startswith("data:"):
                continue
            import json

            obj = json.loads(line[5:].strip())
            if obj["type"] == "delta":
                buffer += obj["text"]
            elif obj["type"] == "done":
                done = obj
            elif obj["type"] == "error":
                print("ERROR:", obj["message"])
                return

    if done:
        print("======== 创建过程 ========")
        print(done.get("process", "")[:1500])
        print("\n======== 人物卡 ========")
        d = done["draft"]
        print(d["name"], "-", d.get("title"))
        print("stats:", d.get("stats", {}).get("strength"), "等")
    else:
        print("未拿到 done 事件,原始输出前 500 字:")
        print(buffer[:500])


if __name__ == "__main__":
    main()
