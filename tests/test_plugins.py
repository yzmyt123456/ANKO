"""插件加载测试:使用真实 plugins 目录中的示例插件。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from anko.app import create_app
from anko.config import DatabaseSettings, PluginSettings, Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _plugin_app() -> TestClient:
    settings = Settings(
        database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
        plugins=PluginSettings(directory=str(PROJECT_ROOT / "plugins")),
    )
    return TestClient(create_app(settings))


def test_example_plugin_route() -> None:
    client = _plugin_app()
    resp = client.get("/api/example/ping")
    assert resp.status_code == 200
    assert resp.json() == {"msg": "pong", "plugin": "example"}


def test_example_plugin_rule() -> None:
    """示例插件注册的 d20 二值规则应生效。"""
    client = _plugin_app()
    resp = client.post("/api/rolls", json={"expression": "d20"})
    assert resp.status_code == 201
    judgement = resp.json()["record"]["judgement"]
    assert judgement is not None
    assert judgement["code"] in {"success", "fail"}
