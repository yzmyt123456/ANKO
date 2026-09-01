"""骰子表达式解析与求值测试。"""

from __future__ import annotations

import random

import pytest

from anko.dice.expression import DiceExprError, parse, roll_expression


class TestParse:
    def test_simple_dice(self) -> None:
        parse("1d100")

    def test_default_count(self) -> None:
        parse("d20")

    def test_dice_with_bonus(self) -> None:
        parse("2d6+3")

    def test_complex(self) -> None:
        parse("2d6+3*2-1")

    def test_parens(self) -> None:
        parse("(1d6+1)*2")

    def test_uppercase_dice(self) -> None:
        parse("D100")


class TestRoll:
    def test_bounds(self) -> None:
        result = roll_expression("1d100")
        assert 1 <= result.total <= 100
        assert len(result.parts) == 1
        part = result.parts[0]
        assert part.kind == "roll"
        assert part.results == [result.total]

    def test_2d6_range(self) -> None:
        for _ in range(50):
            result = roll_expression("2d6")
            assert 2 <= result.total <= 12
        assert len(roll_expression("2d6").parts[0].results) == 2

    def test_bonus_applied(self) -> None:
        result = roll_expression("1d6+10")
        assert 11 <= result.total <= 16

    def test_reproducible_with_seed(self) -> None:
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        assert roll_expression("3d6+1", rng1).total == roll_expression(
            "3d6+1", rng2
        ).total

    def test_describe(self) -> None:
        text = roll_expression("1d100", random.Random(1)).describe()
        assert "1d100" in text


class TestInvalid:
    @pytest.mark.parametrize(
        "expr",
        [
            "",
            "abc",
            "1d",
            "d",
            "1d0",
            "0d6",
            "2d6+",
            "1d100>70",
            "1d100x",
            "()",
        ],
    )
    def test_invalid_expressions(self, expr: str) -> None:
        with pytest.raises(DiceExprError):
            roll_expression(expr)
