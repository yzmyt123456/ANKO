"""AI JSON 宽容解析测试(尾随逗号等 AI 常见错误)。"""

from __future__ import annotations

import pytest

from anko.ai.service import extract_json, normalize_dnd_draft
from anko.ai.client import AIError


class TestLenientJson:
    def test_trailing_commas_in_object(self) -> None:
        text = """{
  "name": "露榭·锻叶",
  "stats": {
    "strength": 11,
    "dexterity": 20,
    "faith": "自然之魂",
  },
  "tags": ["炉火", "野草",]
}"""
        data = extract_json(text)
        assert data["name"] == "露榭·锻叶"
        assert data["stats"]["dexterity"] == 20
        assert data["tags"] == ["炉火", "野草"]

    def test_commas_inside_string_not_removed(self) -> None:
        # 字符串内部包含 ",}" 不应被误删
        text = '{"bio": "背景是 a,} 这样的文本", "faith": "自然之魂",}'
        data = extract_json(text)
        assert data["bio"] == "背景是 a,} 这样的文本"
        assert data["faith"] == "自然之魂"

    def test_no_trailing_commas_still_ok(self) -> None:
        text = '{"name": "正常", "stats": {"wisdom": 16}}'
        assert extract_json(text)["name"] == "正常"

    def test_real_user_case(self) -> None:
        """用户实际遇到的 JSON(尾随逗号)。"""
        text = """{
  "name": "露榭·锻叶",
  "title": "槲寄生下的造物者",
  "bio": "月精灵出身的工匠之女。",
  "stats": {
    "alignment": "混乱善良",
    "race": "精灵（月精灵）",
    "klass": "德鲁伊",
    "level": "1级",
    "hp": "10",
    "strength": 11,
    "dexterity": 20,
    "constitution": 10,
    "intelligence": 18,
    "wisdom": 16,
    "charisma": 15,
    "ac": "15（镶嵌皮甲）",
    "faith": "自然之魂",
  },
  "tags": ["炉火与野草", "月下低语"]
}"""
        draft = normalize_dnd_draft(extract_json(text))
        assert draft["name"] == "露榭·锻叶"
        assert draft["stats"]["dexterity"] == 20
        assert draft["stats"]["faith"] == "自然之魂"
        assert draft["tags"] == ["炉火与野草", "月下低语"]

    def test_invalid_still_raises(self) -> None:
        with pytest.raises(AIError):
            extract_json("{name: 不是合法json}")
