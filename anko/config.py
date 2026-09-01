"""全局配置加载。

支持从 config/settings.yaml 读取配置,所有字段都有默认值,
未提供的字段使用默认值,便于后续扩展。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

# 项目根目录:anko/config.py 的上上级
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


class AppSettings(BaseModel):
    """应用基础信息。"""

    name: str = "安科创作平台"
    debug: bool = True


class ServerSettings(BaseModel):
    """HTTP 服务设置。"""

    host: str = "127.0.0.1"
    port: int = 8000
    api_prefix: str = "/api"


class DatabaseSettings(BaseModel):
    """数据库设置。

    默认使用 SQLite;后续切换到 PostgreSQL / MySQL 只需修改 url,
    存储层通过接口隔离,无需改动业务代码。
    """

    url: str = "sqlite:///./data/anko.db"
    echo: bool = False


class DiceSettings(BaseModel):
    """骰子引擎默认行为。"""

    default_maid: str = "命运之骰"


class PluginSettings(BaseModel):
    """插件系统设置。"""

    directory: str = "plugins"


class AISettings(BaseModel):
    """AI 助手设置(OpenAI 兼容接口)。

    兼容 DeepSeek / OpenAI / 通义千问 / Kimi / Ollama 等任何
    OpenAI 格式的 API。只需配置 base_url 与 api_key。
    """

    enabled: bool = False
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    model: str = "deepseek-chat"
    timeout: float = 30.0


class Settings(BaseModel):
    """全局配置聚合。"""

    app: AppSettings = AppSettings()
    server: ServerSettings = ServerSettings()
    database: DatabaseSettings = DatabaseSettings()
    dice: DiceSettings = DiceSettings()
    plugins: PluginSettings = PluginSettings()
    ai: AISettings = AISettings()


def load_settings(path: Optional[str | Path] = None) -> Settings:
    """加载配置。

    若指定路径的文件存在则加载并覆盖默认值,否则全部使用默认值。
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data: dict = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        data = raw if isinstance(raw, dict) else {}
    return Settings.model_validate(data)
