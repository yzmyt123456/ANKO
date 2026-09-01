"""插件加载器与管理器。

约定:
- 插件位于配置的插件目录(默认 plugins/)下,可以是:
    * 单文件  xxx.py
    * 包      xxx/__init__.py
- 插件模块内需要提供:
    * 变量 `plugin`(AnkoPlugin 实例),或
    * 函数 `setup(context)`(接收 PluginContext)
- 插件通过 PluginContext 注册路由、扩展骰子引擎等。
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from anko.config import Settings
from anko.core.plugin import AnkoPlugin, PluginContext

logger = logging.getLogger("anko.plugins")


class PluginManager:
    """扫描并加载插件。"""

    def __init__(
        self,
        directory: str | Path,
        *,
        settings: Optional[Settings] = None,
        dice_engine: Any = None,
        get_service: Optional[Callable[..., object]] = None,
    ) -> None:
        self.directory = Path(directory)
        self.settings = settings
        self.dice_engine = dice_engine
        self.get_service = get_service
        self._loaded: list[AnkoPlugin] = []
        self._routers: list[tuple[str, Any]] = []

    # ---------------- 发现 ----------------
    def discover(self) -> list[Path]:
        """发现插件目录下的候选模块。"""
        if not self.directory.is_dir():
            return []
        candidates: list[Path] = []
        for entry in sorted(self.directory.iterdir()):
            if entry.is_dir() and (entry / "__init__.py").exists():
                candidates.append(entry)
            elif entry.is_file() and entry.suffix == ".py":
                candidates.append(entry)
        return candidates

    # ---------------- 加载 ----------------
    def load(self) -> list[AnkoPlugin]:
        """加载所有插件,返回成功加载的插件列表。"""
        self._loaded.clear()
        self._routers.clear()

        candidates = self.discover()
        if not candidates:
            return []

        # 确保插件包可以从 sys.path 导入
        root = str(self.directory.parent)
        if root not in sys.path:
            sys.path.insert(0, root)

        context = PluginContext(
            settings=self.settings,
            dice_engine=self.dice_engine,
            get_service=self.get_service,
        )
        package_name = self.directory.name

        for candidate in candidates:
            module_name = f"{package_name}.{candidate.stem}"
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("加载插件 %s 失败:%s", module_name, exc)
                continue

            plugin = getattr(module, "plugin", None)
            if isinstance(plugin, AnkoPlugin):
                try:
                    plugin.setup(context)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("插件 %s setup 失败:%s", module_name, exc)
                    continue
                self._loaded.append(plugin)
                logger.info("已加载插件:%s v%s", plugin.name, plugin.version)
            elif callable(getattr(module, "setup", None)):
                try:
                    module.setup(context)  # type: ignore[attr-defined]
                except Exception as exc:  # noqa: BLE001
                    logger.warning("插件 %s setup 失败:%s", module_name, exc)
                    continue
                logger.info("已加载插件模块:%s", module_name)
            else:
                logger.warning(
                    "跳过 %s:未找到 plugin 实例或 setup 函数", module_name
                )

        self._routers = context.routers
        return list(self._loaded)

    @property
    def routers(self) -> list[tuple[str, Any]]:
        """插件注册的路由列表 [(prefix, APIRouter), ...]。"""
        return list(self._routers)
