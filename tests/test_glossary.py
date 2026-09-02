"""DND 词条系统测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anko.app import create_app
from anko.config import DatabaseSettings, PluginSettings, Settings
from anko.glossary import find_entries, linkify, list_entries


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
        plugins=PluginSettings(directory="__no_plugins__"),
    )
    return TestClient(create_app(settings))


class TestGlossaryCore:
    def test_list_entries(self) -> None:
        entries = list_entries()
        names = {e["name"] for e in entries}
        assert "魔法飞弹" in names
        assert "感知" in names
        assert "术士" in names
        # 名称最长优先
        assert len(entries) == len({e["name"] for e in entries})

    def test_list_entries_filter(self) -> None:
        spells = list_entries("spell")
        assert spells
        assert all(e["category"] == "spell" for e in spells)
        assert "火球术" in {e["name"] for e in spells}

    def test_url_format(self) -> None:
        entries = list_entries("spell")
        fireball = next(e for e in entries if e["name"] == "火球术")
        assert fireball["url"] == "https://dnd.huijiwiki.com/wiki/火球术"

    def test_find_entries(self) -> None:
        hits = find_entries("丰川祥子施展了易容术,又掷出魔法飞弹")
        names = [h["name"] for h in hits]
        assert "易容术" in names
        assert "魔法飞弹" in names

    def test_linkify(self) -> None:
        segments = linkify("她掷出魔法飞弹,同时用游说说服了守卫")
        texts = [s["text"] for s in segments]
        assert "魔法飞弹" in texts
        assert "游说" in texts
        linked = [s for s in segments if s["entry"]]
        assert any(s["entry"]["category"] == "spell" for s in linked)
        # 片段拼接回原文
        assert "".join(s["text"] for s in segments) == "她掷出魔法飞弹,同时用游说说服了守卫"

    def test_linkify_no_match(self) -> None:
        segments = linkify("今天天气不错")
        assert len(segments) == 1
        assert segments[0]["entry"] is None

    def test_linkify_empty(self) -> None:
        assert linkify("") == []


class TestGlossaryAPI:
    def test_list(self, client: TestClient) -> None:
        resp = client.get("/api/glossary")
        assert resp.status_code == 200
        assert len(resp.json()) > 50

    def test_list_filter(self, client: TestClient) -> None:
        resp = client.get("/api/glossary?category=spell")
        assert resp.status_code == 200
        assert all(e["category"] == "spell" for e in resp.json())

    def test_linkify_api(self, client: TestClient) -> None:
        resp = client.post(
            "/api/glossary/linkify",
            json={"text": "他使用了火球术,还带了把长剑。"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hits"] == ["火球术", "长剑"]
        assert any(
            seg["entry"] and seg["entry"]["name"] == "火球术"
            for seg in data["segments"]
        )
