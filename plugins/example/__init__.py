"""示例插件:展示如何扩展平台。

功能:
1. 注册一个自定义判定规则 "d20-binary"(d20,出目 >= 10 成功)
2. 提供一个插件路由 GET /api/example/ping

参考:后续你写的功能插件都放在这里(一个目录/文件一个插件)。
"""

from __future__ import annotations

from fastapi import APIRouter

from anko.core.plugin import AnkoPlugin
from anko.dice.rules import Judgement, JudgementRule


class D20BinaryRule(JudgementRule):
    """极简二值判定:d20,出目 >= 10 成功。"""

    name = "d20-binary"

    def applies(self, expression: str) -> bool:
        return expression.strip().lower() == "d20"

    def judge(self, total: int, expression: str, config: dict) -> Judgement:
        if total >= 10:
            return Judgement("success", "成功", f"出目 {total} ≥ 10:成功。")
        return Judgement("fail", "失败", f"出目 {total} < 10:失败。")


class ExamplePlugin(AnkoPlugin):
    name = "example"
    version = "0.1.0"
    description = "示例插件:注册自定义规则与路由"

    def setup(self, context) -> None:
        # 1. 注册自定义判定规则(通过骰娘 settings 可切换使用)
        if context.dice_engine is not None:
            context.dice_engine.register_rule(D20BinaryRule())

        # 2. 注册一个示例路由
        router = APIRouter(prefix="/example", tags=["示例插件"])

        @router.get("/ping")
        def ping() -> dict:
            return {"msg": "pong", "plugin": self.name}

        context.add_router(router)


# 约定:模块内的 `plugin` 变量会被自动加载
plugin = ExamplePlugin()
