"""API 集成测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    """根路径返回前端页面。"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "安科创作平台" in resp.text


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


class TestCharacters:
    def test_crud(self, client: TestClient) -> None:
        # 创建
        resp = client.post(
            "/api/characters",
            json={
                "name": "爱丽丝",
                "title": "黄昏的旅人",
                "attributes": {"力量": 10, "敏捷": 14},
                "tags": ["主角"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        cid = data["id"]
        assert data["name"] == "爱丽丝"
        assert data["attributes"]["敏捷"] == 14

        # 查询
        assert client.get(f"/api/characters/{cid}").status_code == 200
        assert len(client.get("/api/characters").json()) == 1

        # 更新
        resp = client.put(
            f"/api/characters/{cid}", json={"bio": "来自边境的小镇"}
        )
        assert resp.json()["bio"] == "来自边境的小镇"

        # 删除
        assert client.delete(f"/api/characters/{cid}").status_code == 204
        assert client.get(f"/api/characters/{cid}").status_code == 404

    def test_missing_character(self, client: TestClient) -> None:
        assert client.get("/api/characters/999").status_code == 404


class TestStories:
    def test_story_with_entries(self, client: TestClient) -> None:
        resp = client.post(
            "/api/stories", json={"title": "勇者物语", "tags": ["冒险"]}
        )
        assert resp.status_code == 201
        sid = resp.json()["id"]

        resp = client.post(
            f"/api/stories/{sid}/entries",
            json={"chapter": "序章", "content": "一切从黄昏开始……"},
        )
        assert resp.status_code == 201
        eid = resp.json()["id"]
        assert eid >= 1

        entries = client.get(f"/api/stories/{sid}/entries").json()
        assert len(entries) == 1
        assert entries[0]["chapter"] == "序章"

    def test_entry_on_missing_story(self, client: TestClient) -> None:
        resp = client.post(
            "/api/stories/999/entries", json={"content": "无"}
        )
        assert resp.status_code == 404


class TestMaids:
    def test_default_maid(self, client: TestClient) -> None:
        resp = client.get("/api/maids")
        assert resp.status_code == 200
        names = [m["name"] for m in resp.json()]
        assert "命运之骰" in names

    def test_create_maid_and_duplicate(self, client: TestClient) -> None:
        resp = client.post(
            "/api/maids",
            json={
                "name": "傲娇小掷",
                "default_expression": "2d6",
                "settings": {"threshold": 7},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["is_system"] is False

        dup = client.post("/api/maids", json={"name": "傲娇小掷"})
        assert dup.status_code == 409

    def test_system_maid_not_deletable(self, client: TestClient) -> None:
        maids = client.get("/api/maids").json()
        system = [m for m in maids if m["is_system"]][0]
        assert client.delete(f"/api/maids/{system['id']}").status_code == 400


class TestRolls:
    def test_roll_default_maid(self, client: TestClient) -> None:
        resp = client.post("/api/rolls", json={"expression": "1d100"})
        assert resp.status_code == 201
        data = resp.json()
        assert 1 <= data["record"]["total"] <= 100
        assert data["record"]["judgement"]["code"] in {
            "crit_fail",
            "fail",
            "success",
            "crit_success",
        }
        assert data["description"]

    def test_roll_no_save(self, client: TestClient) -> None:
        resp = client.post(
            "/api/rolls", json={"expression": "2d6", "save": False}
        )
        assert resp.status_code == 201
        assert resp.json()["record"]["id"] == 0
        # 未落库
        assert client.get("/api/rolls").json() == []

    def test_roll_invalid_expression(self, client: TestClient) -> None:
        assert (
            client.post("/api/rolls", json={"expression": "abc"}).status_code
            == 400
        )

    def test_roll_unknown_maid(self, client: TestClient) -> None:
        assert (
            client.post("/api/rolls", json={"maid_id": 999}).status_code == 404
        )

    def test_roll_history(self, client: TestClient) -> None:
        client.post("/api/rolls", json={"expression": "1d100"})
        client.post("/api/rolls", json={"expression": "1d20"})
        assert len(client.get("/api/rolls").json()) == 2
