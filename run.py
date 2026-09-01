"""安科创作平台启动入口。

用法:
    python run.py            # 启动服务
    python run.py --port 9000
"""

from __future__ import annotations

import argparse

import uvicorn

from anko.app import create_app
from anko.config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="安科创作平台")
    parser.add_argument("--host", default=None, help="监听地址")
    parser.add_argument("--port", type=int, default=None, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开发热重载")
    args = parser.parse_args()

    settings = load_settings()
    if args.host:
        settings.server.host = args.host
    if args.port:
        settings.server.port = args.port

    app = create_app(settings)
    uvicorn.run(
        app,
        host=settings.server.host,
        port=settings.server.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
