"""AI 运行时配置 API 测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anko.app import create_app
from anko.config import (
    AISettings,
    DatabaseSettings,
    PluginSettings,
    Settings,
)
from anko.services.config import mask_api_key


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
        plugins=PluginSettings(directory="__no_plugins__"),
        ai=AISettings(enabled=False, api_key=""),
    )
    return TestClient(create_app(settings))


class TestMask:
    def test_mask(self) -> None:
        assert mask_api_key("sk-abcdef123456") == "sk-a****3456"
        assert mask_api_key("short") == "****"
        assert mask_api_key("") == ""


class TestAIConfigAPI:
    def test_get_default(self, client: TestClient) -> None:
        resp = client.get("/api/ai/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["base_url"] == "https://api.deepseek.com/v1"
        assert data["has_api_key"] is False

    def test_update_and_persist(self, client: TestClient) -> None:
        resp = client.put(
            "/api/ai/config",
            json={
                "enabled": True,
                "base_url": "https://api.example.com/v1",
                "api_key": "sk-secret123",
                "model": "test-model",
                "timeout": 60,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["base_url"] == "https://api.example.com/v1"
        assert data["model"] == "test-model"
        assert data["has_api_key"] is True
        # api_key 掩码,不泄露明文
        assert "secret" not in resp.text

        # 再次读取,已持久化
        data2 = client.get("/api/ai/config").json()
        assert data2["enabled"] is True
        assert data2["base_url"] == "https://api.example.com/v1"
        assert data2["has_api_key"] is True

        # status 反映启用状态
        status = client.get("/api/ai/status").json()
        assert status["enabled"] is True

    def test_keep_key_when_masked(self, client: TestClient) -> None:
        client.put(
            "/api/ai/config", json={"enabled": True, "api_key": "sk-secret456"}
        )
        # 传掩码/空:保留原 key
        client.put(
            "/api/ai/config", json={"model": "new-model"}
        )
        data = client.get("/api/ai/config").json()
        assert data["has_api_key"] is True
        assert data["model"] == "new-model"

    def test_clear_key(self, client: TestClient) -> None:
        client.put("/api/ai/config", json={"api_key": "sk-secret456"})
        client.put("/api/ai/config", json={"api_key": ""})
        data = client.get("/api/ai/config").json()
        assert data["has_api_key"] is False

    def test_test_endpoint_requires_config(self, client: TestClient) -> None:
        resp = client.post("/api/ai/test")
        assert resp.status_code == 400

    async def test_test_endpoint_ok(
        self, client: TestClient, monkeypatch
    ) -> None:
        client.put("/api/ai/config", json={"enabled": True, "api_key": "sk-test"})

        async def fake_chat(self, messages):
            return "OK"

        monkeypatch.setattr("anko.ai.service.AIClient.chat", fake_chat)
        resp = client.post("/api/ai/test")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["reply"] == "OK"
