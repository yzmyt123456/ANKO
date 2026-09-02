"""本地 DND 规则库测试(用内存库 + 手工注入样例数据)。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anko.app import create_app
from anko.config import DatabaseSettings, PluginSettings, Settings
from anko.models import RuleKnowledge, RuleMonster, RuleSpell


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
        plugins=PluginSettings(directory="__no_plugins__"),
    )
    app = create_app(settings)
    # 注入样例规则数据
    sf = app.state.storage._session_factory  # noqa: SLF001
    with sf() as s:
        s.add(RuleSpell(
            name="火球术", name_en="Fireball", level=3, school="塑能",
            casting_time="1 动作", range="150 尺",
            components="V、S、M", duration="立即",
            description="在目标点爆发出烈焰……",
        ))
        s.add(RuleSpell(name="魔法飞弹", name_en="Magic Missile", level=1,
                        school="塑能", description="自动命中的飞弹。"))
        s.add(RuleMonster(
            name="底栖魔鱼", name_en="Aboleth",
            meta="大型异怪,守序邪恶", ac="17", hp="135",
            abilities={"力量": 21, "敏捷": 9},
        ))
        s.add(RuleKnowledge(
            book="玩家手册", page=13, title="六项属性",
            content="随机产生你角色的六项属性值……力量敏捷体质智力感知魅力。",
        ))
        s.commit()
    return TestClient(app)


class TestRulesAPI:
    def test_status(self, client: TestClient) -> None:
        resp = client.get("/api/rules/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["spells"] == 2
        assert data["monsters"] == 1
        assert data["imported"] is True

    def test_search_spells(self, client: TestClient) -> None:
        resp = client.get("/api/rules/spells?q=火球")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "火球术"
        assert data[0]["level"] == 3

    def test_get_spell(self, client: TestClient) -> None:
        resp = client.get("/api/rules/spells/魔法飞弹")
        assert resp.status_code == 200
        assert resp.json()["name_en"] == "Magic Missile"

    def test_get_spell_not_found(self, client: TestClient) -> None:
        assert client.get("/api/rules/spells/不存在").status_code == 404

    def test_monsters(self, client: TestClient) -> None:
        resp = client.get("/api/rules/monsters?q=底栖")
        assert resp.status_code == 200
        assert resp.json()[0]["ac"] == "17"

    def test_search_knowledge(self, client: TestClient) -> None:
        resp = client.get("/api/rules/search?q=属性")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["book"] == "玩家手册"

    def test_status_empty(self) -> None:
        settings = Settings(
            database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
            plugins=PluginSettings(directory="__no_plugins__"),
        )
        c = TestClient(create_app(settings))
        assert c.get("/api/rules/status").json()["imported"] is False
