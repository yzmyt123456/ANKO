"""系统配置服务:运行时读写配置(如 AI 配置),保存后立即生效。"""

from __future__ import annotations

from typing import Any, Optional

from anko.config import AISettings
from anko.core.interfaces import Storage

# 配置键
KEY_AI = "ai"


def mask_api_key(api_key: str) -> str:
    """掩码 API Key:保留前 4 与后 4 位。"""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"


class ConfigService:
    """系统运行时配置。"""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    # ---------------- AI 配置 ----------------
    def get_ai_settings(self, default: AISettings) -> AISettings:
        """读取当前 AI 配置(DB 优先,无则用默认)。"""
        data = self._storage.get_config(KEY_AI)
        if not data:
            return default
        merged = {**default.model_dump(), **data}
        return AISettings(**merged)

    def get_ai_config(self, default: AISettings) -> dict:
        """返回 AI 配置(api_key 掩码),供前端展示。"""
        s = self.get_ai_settings(default)
        return {
            "enabled": s.enabled,
            "base_url": s.base_url,
            "model": s.model,
            "timeout": s.timeout,
            "api_key_masked": mask_api_key(s.api_key),
            "has_api_key": bool(s.api_key),
        }

    def update_ai_config(
        self, data: dict, default: AISettings
    ) -> dict:
        """更新 AI 配置并持久化,返回更新后的掩码配置。"""
        current = self.get_ai_settings(default).model_dump()
        for key in ("enabled", "base_url", "model", "timeout"):
            if key in data and data[key] is not None:
                current[key] = data[key]
        # api_key:仅当请求包含该字段时才处理;传新值更新,传掩码/空串保留
        if "api_key" in data:
            new_key = (data.get("api_key") or "").strip()
            if new_key and not new_key.startswith("****"):
                current["api_key"] = new_key
            elif not new_key:
                current["api_key"] = ""
        self._storage.set_config(KEY_AI, current)
        return self.get_ai_config(default)
