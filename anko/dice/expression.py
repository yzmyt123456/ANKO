"""骰子表达式解析与求值。

支持语法(不区分大小写):
  骰子    1d100、d20、2d6
  数字    5、-3
  运算    +  -  *  /
  括号    ( )
示例:2d6+3、1d100-10、(2d6+1)*2

使用手写递归下降解析器 + AST,而非 eval,安全且易于扩展
(例如未来可加 "XdYHZ"(取最大 Z 个)等扩展语法)。
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Optional, Sequence


class DiceExprError(ValueError):
    """表达式语法错误或求值错误。"""


@dataclass
class RollPart:
    """表达式某一部分的执行结果。"""

    kind: str  # "roll" 或 "num"
    label: str  # 原始文本,如 "1d100"
    value: int  # 该部分对总值的贡献
    results: list[int] = field(default_factory=list)  # roll 时每粒骰子结果


@dataclass
class RollResult:
    """一次掷骰的完整结果。"""

    expression: str
    total: int
    parts: list[RollPart]

    def describe(self) -> str:
        """生成人类可读的掷骰描述,如 "1d100+2 => (67)+2 = 69"。 """
        detail = " + ".join(
            p.label if p.kind == "num" else "(" + "+".join(map(str, p.results)) + ")"
            for p in self.parts
        )
        return f"{self.expression} => {detail} = {self.total}"


# ------------------------- AST 节点 -------------------------


class Node:
    """表达式 AST 节点基类。"""

    def eval(self, rng: random.Random) -> tuple[int, list[RollPart]]:  # pragma: no cover
        raise NotImplementedError


class NumNode(Node):
    def __init__(self, value: int, label: str) -> None:
        self.value = value
        self.label = label

    def eval(self, rng: random.Random) -> tuple[int, list[RollPart]]:
        return self.value, [RollPart("num", self.label, self.value)]


class DiceNode(Node):
    def __init__(self, count: int, faces: int, label: str) -> None:
        if count <= 0:
            raise DiceExprError(f"骰子数量必须大于 0:{label}")
        if faces <= 0:
            raise DiceExprError(f"骰子面数必须大于 0:{label}")
        self.count = count
        self.faces = faces
        self.label = label

    def eval(self, rng: random.Random) -> tuple[int, list[RollPart]]:
        results = [rng.randint(1, self.faces) for _ in range(self.count)]
        return sum(results), [
            RollPart("roll", self.label, sum(results), results)
        ]


class BinOpNode(Node):
    def __init__(self, op: str, left: Node, right: Node) -> None:
        self.op = op
        self.left = left
        self.right = right

    def eval(self, rng: random.Random) -> tuple[int, list[RollPart]]:
        lv, lp = self.left.eval(rng)
        rv, rp = self.right.eval(rng)
        if self.op == "+":
            value = lv + rv
        elif self.op == "-":
            value = lv - rv
        elif self.op == "*":
            value = lv * rv
        elif self.op == "/":
            if rv == 0:
                raise DiceExprError("除数不能为 0")
            value = lv // rv
        else:  # pragma: no cover
            raise DiceExprError(f"未知运算符:{self.op}")
        return value, lp + rp


class NegNode(Node):
    def __init__(self, operand: Node) -> None:
        self.operand = operand

    def eval(self, rng: random.Random) -> tuple[int, list[RollPart]]:
        value, parts = self.operand.eval(rng)
        return -value, parts


# ------------------------- 词法 / 语法 -------------------------

_TOKEN_RE = re.compile(
    r"""
    \s*
    (?:
        (?P<dice>(\d*)[dD](\d+))
      | (?P<num>\d+)
      | (?P<plus>\+)
      | (?P<minus>-)
      | (?P<star>\*)
      | (?P<slash>/)
      | (?P<lpar>\()
      | (?P<rpar>\))
    )
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Token:
    kind: str
    text: str


def _tokenize(expression: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    length = len(expression)
    while pos < length:
        m = _TOKEN_RE.match(expression, pos)
        if not m:
            raise DiceExprError(f"无法解析的字符:{expression[pos:]!r} (位置 {pos})")
        if m.group("num") is not None:
            tokens.append(Token("num", m.group("num")))
        elif m.group("dice") is not None:
            tokens.append(Token("dice", m.group(0).strip()))
        elif m.group("plus") is not None:
            tokens.append(Token("+", "+"))
        elif m.group("minus") is not None:
            tokens.append(Token("-", "-"))
        elif m.group("star") is not None:
            tokens.append(Token("*", "*"))
        elif m.group("slash") is not None:
            tokens.append(Token("/", "/"))
        elif m.group("lpar") is not None:
            tokens.append(Token("(", "("))
        elif m.group("rpar") is not None:
            tokens.append(Token(")", ")"))
        pos = m.end()
    return tokens


class _Parser:
    """递归下降解析器。文法:

    expr    := term (('+' | '-') term)*
    term    := factor (('*' | '/') factor)*
    factor  := '-' factor | primary
    primary := NUMBER | DICE | '(' expr ')'
    """

    def __init__(self, tokens: Sequence[Token]) -> None:
        self.tokens = list(tokens)
        self.pos = 0

    def peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, kind: str) -> Token:
        token = self.peek()
        if token is None or token.kind != kind:
            raise DiceExprError(f"预期 {kind!r},但遇到 {token!r}")
        self.pos += 1
        return token

    def parse(self) -> Node:
        if not self.tokens:
            raise DiceExprError("表达式为空")
        node = self._expr()
        if self.peek() is not None:
            raise DiceExprError(f"多余的输入:{self.peek()!r}")
        return node

    def _expr(self) -> Node:
        node = self._term()
        while (tok := self.peek()) is not None and tok.kind in ("+", "-"):
            self.consume(tok.kind)
            node = BinOpNode(tok.kind, node, self._term())
        return node

    def _term(self) -> Node:
        node = self._factor()
        while (tok := self.peek()) is not None and tok.kind in ("*", "/"):
            self.consume(tok.kind)
            node = BinOpNode(tok.kind, node, self._factor())
        return node

    def _factor(self) -> Node:
        tok = self.peek()
        if tok is not None and tok.kind == "-":
            self.consume("-")
            return NegNode(self._factor())
        return self._primary()

    def _primary(self) -> Node:
        tok = self.peek()
        if tok is None:
            raise DiceExprError("意外的表达式结尾")
        if tok.kind == "num":
            self.consume("num")
            return NumNode(int(tok.text), tok.text)
        if tok.kind == "dice":
            self.consume("dice")
            m = re.fullmatch(r"(\d*)[dD](\d+)", tok.text)
            count = int(m.group(1)) if m.group(1) else 1
            faces = int(m.group(2))
            return DiceNode(count, faces, tok.text)
        if tok.kind == "(":
            self.consume("(")
            node = self._expr()
            self.consume(")")
            return node
        raise DiceExprError(f"意外的标记:{tok!r}")


def parse(expression: str) -> Node:
    """解析表达式,返回 AST 根节点。"""
    return _Parser(_tokenize(expression)).parse()


def roll_expression(
    expression: str, rng: Optional[random.Random] = None
) -> RollResult:
    """解析并执行一次掷骰。"""
    rng = rng or random.Random()
    tree = parse(expression)
    total, parts = tree.eval(rng)
    return RollResult(expression=expression, total=total, parts=parts)
