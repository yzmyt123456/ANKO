"""AI 生成角色测试。"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from anko.ai.service import (
    AIService,
    build_generate_prompt,
    normalize_dnd_draft,
)
from anko.app import create_app
from anko.config import (
    AISettings,
    DatabaseSettings,
    PluginSettings,
    Settings,
)


@pytest.fixture
def service() -> AIService:
    return AIService(AISettings(enabled=True, api_key="sk-test"))


class TestGeneratePrompt:
    def test_dnd_prompt_contains_method(self) -> None:
        p = build_generate_prompt("剑湾的冒险", "要一个神秘的角色", "dnd5e")
        assert "骰点创建法" in p
        assert "剑湾的冒险" in p
        assert "要一个神秘的角色" in p
        assert '"strength"' in p
        # 选项列表与选中项加粗要求
        assert "列出全部选项" in p
        assert "**" in p

    def test_default_prompt(self) -> None:
        p = build_generate_prompt("", "", "default")
        assert "attributes" in p
        # 空上下文有兜底文案
        assert "自由发挥" in p

    def test_hint_fallback(self) -> None:
        p = build_generate_prompt("", "", "dnd5e")
        assert "无特别要求" in p


class TestGenerateCharacter:
    async def test_generate_dnd(self, service: AIService, monkeypatch) -> None:
        async def fake_chat(self, messages):
            return json.dumps(
                {
                    "name": "爱丽丝",
                    "title": "流浪剑士",
                    "bio": "来自剑湾的孤狼剑士。",
                    "stats": {
                        "alignment": "中立善良",
                        "race": "人类",
                        "klass": "战士",
                        "strength": 16,
                        "dexterity": 14,
                        "constitution": 13,
                        "intelligence": 10,
                        "wisdom": 9,
                        "charisma": 12,
                    },
                    "tags": ["战士", "剑湾"],
                }
            )

        monkeypatch.setattr("anko.ai.service.AIClient.chat", fake_chat)
        draft = await service.generate_character(
            story_context="剑湾的冒险", hint="", template="dnd5e"
        )
        assert draft["template"] == "dnd5e"
        assert draft["name"] == "爱丽丝"
        assert draft["stats"]["strength"] == 16
        assert draft["stats"]["race"] == "人类"


class TestGenerateAPI:
    @pytest.fixture
    def client(self) -> TestClient:
        settings = Settings(
            database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
            plugins=PluginSettings(directory="__no_plugins__"),
            ai=AISettings(enabled=True, api_key="sk-test"),
        )
        return TestClient(create_app(settings))

    def _make_client(self) -> TestClient:
        settings = Settings(
            database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
            plugins=PluginSettings(directory="__no_plugins__"),
            ai=AISettings(enabled=True, api_key="sk-test"),
        )
        return TestClient(create_app(settings))

    def test_generate_disabled(self) -> None:
        settings = Settings(
            database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
            plugins=PluginSettings(directory="__no_plugins__"),
            ai=AISettings(enabled=False, api_key=""),
        )
        client = TestClient(create_app(settings))
        resp = client.post(
            "/api/ai/generate-character",
            json={"story_context": "剑湾", "template": "dnd5e"},
        )
        assert resp.status_code == 503

    async def test_generate_ok(
        self, client: TestClient, monkeypatch
    ) -> None:
        async def fake_chat(self, messages):
            return json.dumps(
                {
                    "name": "雷恩",
                    "title": "雇佣兵",
                    "stats": {"strength": 18, "charisma": 14},
                    "tags": ["佣兵"],
                }
            )

        monkeypatch.setattr("anko.ai.service.AIClient.chat", fake_chat)
        resp = client.post(
            "/api/ai/generate-character",
            json={"story_context": "被遗忘的国度", "hint": "独来独往", "template": "dnd5e"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "雷恩"
        assert data["template"] == "dnd5e"
        assert data["stats"]["strength"] == 18

    def test_normalize_dnd(self) -> None:
        draft = normalize_dnd_draft(
            {"name": "X", "stats": {"charisma": 20, "wisdom": "9"}}
        )
        assert draft["stats"]["charisma"] == 20
        assert draft["stats"]["wisdom"] == 9


class TestGenerateStreamAPI:
    @pytest.fixture
    def client(self) -> TestClient:
        settings = Settings(
            database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
            plugins=PluginSettings(directory="__no_plugins__"),
            ai=AISettings(enabled=True, api_key="sk-test"),
        )
        return TestClient(create_app(settings))

    async def test_stream_ok(self, client: TestClient, monkeypatch) -> None:
        async def fake_chat_stream(self, messages):
            yield "【创建过程】\n"
            yield "[力量] 两次1d16+2:7+2=9、10+2=12 → 取高12\n"
            yield "【最终人物卡】\n"
            yield '{"name": "雷恩", "stats": {"strength": 18, "charisma": 14}}'

        monkeypatch.setattr(
            "anko.ai.service.AIClient.chat_stream", fake_chat_stream
        )
        with client.stream(
            "POST",
            "/api/ai/generate-character/stream",
            json={"story_context": "剑湾", "template": "dnd5e"},
        ) as resp:
            assert resp.status_code == 200
            body = "".join(resp.iter_text())

        assert '"type": "delta"' in body
        assert '"type": "done"' in body
        assert "雷恩" in body
        assert '"name": "雷恩"' in body
        # 创建过程文本被正确拆分并返回
        assert '"process"' in body
        assert "1d16+2" in body

    async def test_stream_error(self, client: TestClient, monkeypatch) -> None:
        async def fake_chat_stream(self, messages):
            yield ""  # 使函数成为 async generator
            raise ValueError("boom")

        monkeypatch.setattr(
            "anko.ai.service.AIClient.chat_stream", fake_chat_stream
        )
        with client.stream(
            "POST",
            "/api/ai/generate-character/stream",
            json={"template": "dnd5e"},
        ) as resp:
            assert resp.status_code == 200
            body = "".join(resp.iter_text())
        assert '"type": "error"' in body
        assert "boom" in body

