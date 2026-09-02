"""AI 助手模块测试。"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from anko.ai.client import AIError
from anko.ai.service import (
    AIService,
    extract_json,
    normalize_character_draft,
)
from anko.app import create_app
from anko.config import AISettings, DatabaseSettings, PluginSettings, Settings


class TestExtractJson:
    def test_plain_json(self) -> None:
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_fence(self) -> None:
        text = '```json\n{"name": "爱丽丝"}\n```'
        assert extract_json(text) == {"name": "爱丽丝"}

    def test_with_surrounding_text(self) -> None:
        text = '好的,这是整理结果: {"name": "鲍勃", "tags": ["a"]} 完成。'
        assert extract_json(text) == {"name": "鲍勃", "tags": ["a"]}

    def test_missing_json(self) -> None:
        with pytest.raises(AIError):
            extract_json("很抱歉,我无法处理这段文本")

    def test_invalid_json(self) -> None:
        with pytest.raises(AIError):
            extract_json("{name: 不是合法json}")


class TestNormalizeDraft:
    def test_normalize(self) -> None:
        data = {
            "name": " 菲利斯 ",
            "title": "炼金术士",
            "bio": "来自边境小镇。",
            "attributes": {"智慧": 16, "敏捷": 11},
            "tags": ["主角", " 魔法 ", ""],
        }
        draft = normalize_character_draft(data)
        assert draft["name"] == "菲利斯"
        assert draft["title"] == "炼金术士"
        assert draft["attributes"]["智慧"] == 16
        assert draft["tags"] == ["主角", "魔法"]

    def test_missing_fields(self) -> None:
        draft = normalize_character_draft({"name": ""})
        assert draft["name"] == ""
        assert draft["title"] is None
        assert draft["bio"] is None
        assert draft["attributes"] == {}
        assert draft["tags"] == []


class TestAIService:
    @pytest.fixture
    def settings(self) -> AISettings:
        return AISettings(
            enabled=True, api_key="sk-test", model="test-model"
        )

    @pytest.fixture
    def service(self, settings: AISettings) -> AIService:
        return AIService(settings)

    async def test_parse_character(self, service: AIService, monkeypatch) -> None:
        async def fake_chat(self, messages):
            return json.dumps(
                {
                    "name": "雷恩",
                    "title": "雇佣兵",
                    "bio": "无父无母的雇佣兵。",
                    "attributes": {"力量": 18},
                    "tags": ["佣兵", "战斗"],
                }
            )

        monkeypatch.setattr(
            "anko.ai.service.AIClient.chat", fake_chat
        )
        draft = await service.parse_character("雷恩是一名雇佣兵……")
        assert draft["name"] == "雷恩"
        assert draft["attributes"]["力量"] == 18
        assert draft["tags"] == ["佣兵", "战斗"]

    async def test_empty_text(self, service: AIService) -> None:
        with pytest.raises(ValueError):
            await service.parse_character("   ")

    def test_enabled_flag(self, service: AIService, settings: AISettings) -> None:
        assert service.enabled
        off = AIService(AISettings(enabled=False, api_key="sk-test"))
        assert not off.enabled
        empty = AIService(AISettings(enabled=True, api_key=""))
        assert not empty.enabled


class TestAIRoutes:
    def _make_client(self, **ai_kwargs) -> TestClient:
        settings = Settings(
            database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
            plugins=PluginSettings(directory="__no_plugins__"),
            ai=AISettings(**ai_kwargs),
        )
        return TestClient(create_app(settings))

    def test_status_disabled(self) -> None:
        client = self._make_client(enabled=False, api_key="")
        resp = client.get("/api/ai/status")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    def test_parse_when_disabled(self) -> None:
        client = self._make_client(enabled=False, api_key="")
        resp = client.post(
            "/api/ai/parse-character", json={"text": "一名角色描述……"}
        )
        assert resp.status_code == 503
        assert "ai" in resp.json()["detail"].lower()

    def test_parse_empty_text(self) -> None:
        client = self._make_client(enabled=True, api_key="sk-test")
        resp = client.post("/api/ai/parse-character", json={"text": "  "})
        assert resp.status_code == 400

    def test_parse_ai_error(self, monkeypatch) -> None:
        client = self._make_client(enabled=True, api_key="sk-test")

        async def fail_chat(self_, messages):
            raise AIError("boom")

        monkeypatch.setattr(
            "anko.ai.service.AIClient.chat", fail_chat
        )
        resp = client.post(
            "/api/ai/parse-character", json={"text": "一段角色描述"}
        )
        assert resp.status_code == 502
        assert "boom" in resp.json()["detail"]
