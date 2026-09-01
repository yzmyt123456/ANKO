"""冒烟测试:验证平台完整流程(会使用真实 data/anko.db)。

用法: python scripts/smoke_test.py
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from anko.app import create_app


def main() -> None:
    client = TestClient(create_app())
    stamp = str(int(time.time()))  # 唯一后缀,保证脚本可重复运行

    # 1. 系统信息
    health = client.get("/health").json()
    print("HEALTH:", health)
    page = client.get("/")
    print("PAGE:", page.status_code, "text/html" in page.headers["content-type"])

    # 2. 创建人物卡
    r = client.post(
        "/api/characters",
        json={
            "name": f"菲利斯{stamp}",
            "title": "炼金术士",
            "attributes": {"智慧": 16, "敏捷": 11},
            "tags": ["主角", "魔法"],
        },
    )
    char = r.json()
    print("CHAR:", char["id"], char["name"])

    # 3. 创建自定义骰娘
    r = client.post(
        "/api/maids",
        json={
            "name": f"傲娇小掷{stamp}",
            "personality": "哼!",
            "default_expression": "1d100",
            "settings": {"threshold": 55, "crit_success": 96, "crit_fail": 4},
        },
    )
    maid = r.json()
    print("MAID:", maid["id"], maid["name"])

    # 4. 创建剧情并追加条目
    r = client.post(
        "/api/stories", json={"title": f"异世界转生{stamp}", "tags": ["奇幻"]}
    )
    story = r.json()
    print("STORY:", story["id"])
    client.post(
        f"/api/stories/{story['id']}/entries",
        json={
            "chapter": "序章",
            "content": "醒来时,我发现自己躺在一片陌生的麦田里……",
            "character_ids": [char["id"]],
        },
    )

    # 5. 掷骰(指定骰娘)
    r = client.post(
        "/api/rolls",
        json={
            "expression": "1d100",
            "maid_id": maid["id"],
            "context": {"story_id": story["id"], "character_id": char["id"]},
        },
    )
    roll = r.json()
    print(
        "ROLL:",
        roll["record"]["total"],
        roll["record"]["judgement"]["level"],
    )
    print("DESC:", roll["description"].replace("\n", " | "))

    # 6. 掷一个 2d6
    r = client.post("/api/rolls", json={"expression": "2d6+3"})
    print("ROLL2:", r.json()["description"].replace("\n", " | "))

    # 7. 回查剧情与历史
    entries = client.get(f"/api/stories/{story['id']}/entries").json()
    rolls = client.get("/api/rolls").json()
    print("ENTRIES:", len(entries))
    print("ROLLS:", len(rolls))
    print("SMOKE TEST OK")


if __name__ == "__main__":
    main()
