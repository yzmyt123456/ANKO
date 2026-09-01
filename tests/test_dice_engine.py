"""骰子引擎与判定规则测试。"""

from __future__ import annotations

import random

from anko.dice.engine import DiceEngine
from anko.dice.expression import roll_expression
from anko.dice.maids import MaidConfig
from anko.dice.rules import D100Rule


def make_maid(**overrides: object) -> MaidConfig:
    data: dict = {
        "id": 1,
        "name": "测试骰娘",
        "default_expression": "1d100",
        "settings": {},
    }
    data.update(overrides)
    return MaidConfig(**data)


class TestD100Rule:
    def setup_method(self) -> None:
        self.rule = D100Rule()

    def test_applies(self) -> None:
        for expr in ["1d100", "d100", "d100+2", "1d100-10"]:
            assert self.rule.applies(expr), expr
        assert not self.rule.applies("2d6")
        assert not self.rule.applies("1d20")

    def test_levels(self) -> None:
        assert self.rule.judge(100, "1d100", {}).code == "crit_success"
        assert self.rule.judge(95, "1d100", {}).code == "crit_success"
        assert self.rule.judge(1, "1d100", {}).code == "crit_fail"
        assert self.rule.judge(5, "1d100", {}).code == "crit_fail"
        assert self.rule.judge(60, "1d100", {}).code == "success"
        assert self.rule.judge(50, "1d100", {}).code == "fail"
        assert self.rule.judge(30, "1d100", {}).code == "fail"

    def test_custom_threshold(self) -> None:
        config = {"threshold": 70, "crit_success": 98, "crit_fail": 2}
        assert self.rule.judge(80, "1d100", config).code == "success"
        assert self.rule.judge(99, "1d100", config).code == "crit_success"
        assert self.rule.judge(1, "1d100", config).code == "crit_fail"


class TestEngine:
    def setup_method(self) -> None:
        self.engine = DiceEngine()

    def test_roll_without_judgement(self) -> None:
        outcome = self.engine.roll("2d6", maid=make_maid())
        assert outcome.judgement is None
        assert 2 <= outcome.result.total <= 12
        assert outcome.description

    def test_roll_with_judgement(self) -> None:
        outcome = self.engine.roll("1d100", maid=make_maid())
        assert outcome.judgement is not None
        assert outcome.judgement.code in {
            "crit_fail",
            "fail",
            "success",
            "crit_success",
        }
        assert "大成功" in str(outcome.judgement.level) or "成功" in str(
            outcome.judgement.level
        ) or "失败" in str(outcome.judgement.level)

    def test_roll_specific_judgement(self) -> None:
        # 用固定的 rng 序列无法保证出目,改为 monkeypatch 骰子结果
        from anko.dice import expression as expr_module

        original = expr_module.random.Random

        class FixedRandom(random.Random):
            def randint(self, a: int, b: int) -> int:
                return 99

        try:
            expr_module.random.Random = FixedRandom  # type: ignore[assignment]
            outcome = self.engine.roll("1d100", maid=make_maid())
            assert outcome.judgement.code == "crit_success"
        finally:
            expr_module.random.Random = original

    def test_modifiers_add(self) -> None:
        maid = make_maid(settings={"modifiers": [{"type": "add", "value": 5}]})
        rng = random.Random(7)
        outcome = self.engine.roll("1d100", maid=maid, rng=rng)

        base = roll_expression("1d100", random.Random(7)).total
        assert outcome.result.total == base + 5
