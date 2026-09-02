"""DND 模板端到端验证(使用真实 data/anko.db,幂等)。"""

from __future__ import annotations

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> None:
    # 1. 模板列表
    templates = httpx.get(f"{BASE}/api/templates").json()
    print("TEMPLATES:", [t["id"] for t in templates])

    # 2. 模板详情
    dnd = httpx.get(f"{BASE}/api/templates/dnd5e").json()
    print("DND GROUPS:", [g["key"] for g in dnd["groups"]])
    print("DND CHECKS:", len(dnd["checks"]), "项")

    # 3. 创建 DND 人物卡(幂等:带时间戳)
    import time

    stamp = str(int(time.time()))
    stats = {
        "alignment": "中立善良",
        "race": "人类/贵族",
        "klass": "术士/狂野术法(1级)",
        "level": "1级",
        "hp": "7",
        "strength": 12,
        "dexterity": 18,
        "constitution": 13,
        "intelligence": 15,
        "wisdom": 9,
        "charisma": 20,
        "ac": "14",
        "spell_dc": "15",
        "proficiency_bonus": 2,
        "primary_stat": "魅力",
        "save_proficiencies": "体质, 魅力",
        "skill_proficiencies": "奥秘、游说、宗教、历史、表演",
        "equipment": "矛, 2把匕首, 奥术法器(水晶)",
        "languages": "通用语, 矮人语, 精灵语",
        "known_spells": "易容术, 七彩喷射, 雷鸣波(始终准备)",
        "known_cantrips": "术法爆发, 传讯术",
        "class_features": "适应力, 先天术法",
        "feats": "熟习, 魔法学徒",
        "faith": "无信者",
    }
    resp = httpx.post(
        f"{BASE}/api/characters",
        json={"name": f"丰川祥子{stamp}", "title": "狂野术士", "template": "dnd5e", "stats": stats},
    )
    resp.raise_for_status()
    cid = resp.json()["id"]
    print(f"CHAR CREATED: id={cid} template=dnd5e")

    # 4. 鉴定
    for kind, key, label in [
        ("stat", "charisma", "魅力鉴定"),
        ("skill", "perception", "察觉"),
        ("skill", "arcana", "奥秘"),
        ("save", "save_charisma", "魅力豁免"),
    ]:
        r = httpx.post(f"{BASE}/api/characters/{cid}/checks", json={"kind": kind, "key": key})
        d = r.json()
        print(f"CHECK {label}: {d['expression']} = {d['total']} | {d['description'].splitlines()[0]}")

    # 5. 带 DC 判定
    r = httpx.post(f"{BASE}/api/characters/{cid}/checks", json={"kind": "skill", "key": "perception", "dc": 15})
    d = r.json()
    print(f"CHECK 察觉 DC15: {d['expression']} = {d['total']} → {d['judgement']['level'] if d['judgement'] else '无判定'}")

    print("DND SMOKE TEST OK")


if __name__ == "__main__":
    main()
