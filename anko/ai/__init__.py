"""AI 助手模块。

提供 OpenAI 兼容接口的客户端,以及"从大段文本解析结构化数据"的能力
(如 AI 快速建档:粘贴角色描述 → 拆分出名字/称号/背景/属性/标签)。
"""

from anko.ai.service import AIService

__all__ = ["AIService"]
