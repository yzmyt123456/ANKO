"""前端一致性校验:index.html 引用的方法/变量是否在 app.js 中定义。

用法: python scripts/check_frontend.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "anko" / "static" / "index.html"
APPJS = ROOT / "anko" / "static" / "js" / "app.js"


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    js = APPJS.read_text(encoding="utf-8")

    # 1. @click 中引用的方法
    click_methods = set(re.findall(r"@click=\"([a-zA-Z_]\w*)\s*\(", html))
    # 也处理 @click="method" 无括号的情况
    click_methods |= set(re.findall(r"@click=\"([a-zA-Z_]\w*)\"", html))
    click_methods.discard("stop")

    missing = []
    for m in sorted(click_methods):
        # 在 app.js 中找 "m(" 或 "m(" 的定义
        if not re.search(rf"\b{re.escape(m)}\s*\(", js):
            missing.append(m)

    # 2. v-model 引用的变量
    models = set(re.findall(r"v-model(?:\.\w+)?=\"([a-zA-Z_][\w.]*)\"", html))
    for m in sorted(models):
        base = m.split(".")[0]
        if base not in js and base != "rollResult":
            missing.append(f"v-model:{m}")

    print(f"@click 引用方法: {sorted(click_methods)}")
    print(f"v-model 引用: {sorted(models)}")
    if missing:
        print(f"❌ 缺失定义: {sorted(missing)}")
        sys.exit(1)
    print("✅ 前端引用一致性校验通过")


if __name__ == "__main__":
    main()
