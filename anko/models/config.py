"""系统配置存储模型。"""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from anko.models.base import Base


class SystemConfig(Base):
    """运行时配置键值对(如 AI 配置),可在网页上修改并立即生效。"""

    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SystemConfig key={self.key!r}>"
