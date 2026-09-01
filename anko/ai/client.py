"""OpenAI 兼容 API 客户端。

基于 httpx 实现,不依赖特定厂商 SDK;
任何提供 OpenAI 格式接口的服务(DeepSeek / OpenAI / 通义 / Kimi / Ollama)
都可以通过配置 base_url + api_key 接入。
"""

from __future__ import annotations

import httpx

from anko.config import AISettings


class AIError(RuntimeError):
    """AI 服务调用失败。"""


class AIClient:
    """轻量 OpenAI 兼容 Chat Completions 客户端。"""

    def __init__(self, settings: AISettings) -> None:
        self._settings = settings

    @property
    def base_url(self) -> str:
        return self._settings.base_url.rstrip("/")

    async def chat(self, messages: list[dict]) -> str:
        """调用 chat/completions,返回 assistant 回复文本。"""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self._settings.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self._settings.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise AIError(
                f"AI 服务返回 HTTP {exc.response.status_code}: "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.RequestError as exc:
            raise AIError(f"无法连接 AI 服务({exc.request.url}): {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError("AI 响应格式异常(缺少 choices/content)") from exc
