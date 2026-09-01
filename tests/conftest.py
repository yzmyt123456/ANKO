"""pytest 共享 fixture。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anko.app import create_app
from anko.config import DatabaseSettings, PluginSettings, Settings

TEST_SETTINGS = Settings(
    database=DatabaseSettings(url="sqlite:///:memory:", echo=False),
    # 指向不存在的目录,避免测试加载示例插件
    plugins=PluginSettings(directory="__no_plugins__"),
)


@pytest.fixture
def app():
    return create_app(TEST_SETTINGS)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
