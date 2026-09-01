"""插件系统基类。

插件是平台"后续加功能"的主要手段:
- 提供新的 REST API(通过 add_router)
- 注册自定义骰子函数 / 判定规则
- 在 setup 阶段做任何初始化

一个最小插件只需要定义一个继承 AnkoPlugin 的类,并把实例放在
插件模块的 plugin 变量中即可被自动加载。
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:  # 仅类型检查用,避免运行时依赖
    from fastapi import APIRouter
    from anko.config import Settings
    from anko.dice.engine import DiceEngine


@dataclass
class PluginContext:
    """插件运行时上下文:插件通过它访问平台能力。"""

    settings: Optional["Settings"] = None
    dice_engine: Optional["DiceEngine"] = None
    get_service: Optional[Callable[..., object]] = None
    _routers: list = field(default_factory=list)

    def add_router(self, router: "APIRouter", prefix: str = "") -> None:
        """向平台注册一个 FastAPI 路由(插件可提供额外 API)。"""
        self._routers.append((prefix, router))

    @property
    def routers(self) -> list:
        """平台会读取这里收集到的路由并挂载。"""
        return list(self._routers)


class AnkoPlugin(ABC):
    """所有插件的基类。

    子类需要实现 setup(context);平台启动时会调用它。
    加载约定:插件包内必须有名为 `plugin` 的 AnkoPlugin 实例,
    或名为 `setup` 的函数(接收 PluginContext)。
    """

    name: str = "unnamed-plugin"
    version: str = "0.1.0"
    description: str = ""

    def setup(self, context: PluginContext) -> None:
        """插件入口:在这里注册路由 / 骰子函数 / 规则等。"""
