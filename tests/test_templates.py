"""人物卡模板与 DND 鉴定测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anko.ai.service import normalize_dnd_draft
from anko.app import create_app
from anko.config import DatabaseSettings, PluginSettings, Settings


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
        plugins=PluginSettings(directory="__no_plugins__"),
    )
    return TestClient(create_app(settings))


def _make_dnd_character(client: TestClient) -> dict:
    """创建一个丰川祥子风格的 DND 人物卡。"""
    resp = client.post(
        "/api/characters",
        json={
            "name": "丰川祥子",
            "title": "狂野术士",
            "template": "dnd5e",
            "stats": {
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
                "weapon_proficiencies": "简易武器",
                "equipment": "矛, 2把匕首, 奥术法器(水晶)",
                "languages": "通用语, 矮人语, 精灵语",
                "spellcasting_ability": "魅力",
                "spell_slots": "一环法术位(2)",
                "known_spells": "易容术, 七彩喷射, 雷鸣波(始终准备)",
                "known_cantrips": "术法爆发, 传讯术",
                "class_features": "适应力, 先天术法",
                "feats": "熟习, 魔法学徒",
                "faith": "无信者",
            },
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestTemplatesAPI:
    def test_list_templates(self, client: TestClient) -> None:
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        ids = [t["id"] for t in resp.json()]
        assert "default" in ids and "dnd5e" in ids

    def test_template_detail(self, client: TestClient) -> None:
        resp = client.get("/api/templates/dnd5e")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "dnd5e"
        groups = {g["key"]: g for g in data["groups"]}
        assert "stats" in groups
        stat_keys = [f["key"] for f in groups["stats"]["fields"]]
        assert stat_keys == [
            "strength", "dexterity", "constitution",
            "intelligence", "wisdom", "charisma",
        ]
        assert len(data["checks"]) >= 30
        assert any(c["key"] == "perception" and c["kind"] == "skill"
                   for c in data["checks"])

    def test_unknown_template(self, client: TestClient) -> None:
        assert client.get("/api/templates/nope").status_code == 404


class TestDNDChecks:
    def test_create_dnd_character(self, client: TestClient) -> None:
        data = _make_dnd_character(client)
        assert data["template"] == "dnd5e"
        assert data["stats"]["charisma"] == 20
        assert data["stats"]["dexterity"] == 18

    def test_stat_check(self, client: TestClient) -> None:
        char = _make_dnd_character(client)
        resp = client.post(
            f"/api/characters/{char['id']}/checks",
            json={"kind": "stat", "key": "charisma"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["expression"] == "1d20+5"  # 魅力 20 → +5
        assert data["modifier"] == 5
        assert 1 <= data["natural"] <= 20
        assert data["total"] == data["natural"] + 5

    def test_save_check_with_proficiency(self, client: TestClient) -> None:
        """魅力在熟练豁免中:修正 = 魅力(+5) + 熟练加值(2) = +7。"""
        char = _make_dnd_character(client)
        resp = client.post(
            f"/api/characters/{char['id']}/checks",
            json={"kind": "save", "key": "save_charisma"},
        )
        assert resp.status_code == 200
        assert resp.json()["expression"] == "1d20+7"

    def test_check_with_dc(self, client: TestClient) -> None:
        char = _make_dnd_character(client)
        resp = client.post(
            f"/api/characters/{char['id']}/checks",
            json={"kind": "stat", "key": "wisdom", "dc": 15},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["judgement"] is not None
        assert data["judgement"]["code"] in {
            "success", "fail", "crit_success", "crit_fail",
        }

    def test_check_on_default_template(self, client: TestClient) -> None:
        resp = client.post(
            "/api/characters", json={"name": "普通角色"}
        )
        char = resp.json()
        resp = client.post(
            f"/api/characters/{char['id']}/checks",
            json={"kind": "stat", "key": "strength"},
        )
        assert resp.status_code == 400

    def test_unknown_check(self, client: TestClient) -> None:
        char = _make_dnd_character(client)
        resp = client.post(
            f"/api/characters/{char['id']}/checks",
            json={"kind": "skill", "key": "nonexistent"},
        )
        assert resp.status_code == 400

    def test_check_missing_character(self, client: TestClient) -> None:
        resp = client.post(
            "/api/characters/999/checks",
            json={"kind": "stat", "key": "strength"},
        )
        assert resp.status_code == 404


class TestDNDAIParse:
    def test_normalize_dnd_draft(self) -> None:
        data = {
            "name": "丰川祥子",
            "stats": {
                "strength": 12,
                "charisma": 20,
                "skill_proficiencies": "奥秘、游说",
                "known_spells": "易容术, 七彩喷射",
            },
        }
        draft = normalize_dnd_draft(data)
        assert draft["template"] == "dnd5e"
        assert draft["stats"]["strength"] == 12
        assert draft["stats"]["charisma"] == 20
        assert draft["stats"]["known_spells"] == "易容术, 七彩喷射"
        # 未提供的字段:数值为 0,文本为空串
        assert draft["stats"]["ac"] == ""
        assert draft["stats"]["wisdom"] == 0


    def test_skill_check_with_proficiency(self, client: TestClient) -> None:
        """奥秘是熟练技能:修正 = 智力(+2) + 熟练加值(2) = +4。"""
        char = _make_dnd_character(client)
        resp = client.post(
            f"/api/characters/{char['id']}/checks",
            json={"kind": "skill", "key": "arcana"},
        )
        assert resp.status_code == 200
        assert resp.json()["expression"] == "1d20+4"

    def test_skill_check_without_proficiency(self, client: TestClient) -> None:
        """潜行不熟练:仅敏捷修正 +4。"""
        char = _make_dnd_character(client)
        resp = client.post(
            f"/api/characters/{char['id']}/checks",
            json={"kind": "skill", "key": "stealth"},
        )
        assert resp.status_code == 200
        assert resp.json()["expression"] == "1d20+4"
