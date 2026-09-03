"""ASGI 入口(供 uvicorn --reload / 生产服务器直接引用)。

用法:
    python -m uvicorn anko.asgi:app --host 127.0.0.1 --port 8000 --reload
"""

from __future__ import annotations

from anko.app import create_app
from anko.config import load_settings

app = create_app(load_settings())
