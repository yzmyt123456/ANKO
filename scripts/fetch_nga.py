"""抓取 NGA 帖子:模拟 guestJs cookie 验证流程。

用法: python scripts/fetch_nga.py <tid>
"""

from __future__ import annotations

import random
import re
import subprocess
import sys

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def curl(url: str, cookies: str = "") -> tuple[str, list[str]]:
    args = ["curl.exe", "-s", "--max-time", "25", "-L", "-A", UA]
    if cookies:
        args += ["-H", f"Cookie: {cookies}"]
    args.append(url)
    out = subprocess.check_output(
        args, text=True, encoding="gb18030", errors="replace"
    )
    # 用响应头判断:需要 -D 存头?简化:直接返回 body
    return out, []


def main() -> None:
    tid = sys.argv[1] if len(sys.argv) > 1 else "46321088"
    base = f"https://ngabbs.com/read.php?tid={tid}"

    # 1. 第一次请求,提取 guestJs cookie
    body, _ = curl(base)
    m = re.search(r"guestJs=([0-9a-zA-Z_]+)", body)
    if not m:
        print("未找到 guestJs,输出前 500 字符:")
        print(body[:500])
        return
    cookie = f"guestJs={m.group(1)}; lastpath=0"
    print("获取到 guestJs cookie:", m.group(1))

    # 2. 带 cookie 请求(带 rand 参数)
    rand = random.randint(0, 9999)
    body2, _ = curl(f"{base}&rand={rand}", cookie)
    if "guestJs" in body2[:200] and "无法" in body2:
        print("仍被验证,重试…")
        body2, _ = curl(f"{base}&rand={random.randint(0,9999)}", cookie)

    with open("scripts/nga_ok.html", "w", encoding="utf-8") as f:
        f.write(body2)
    print("已保存 scripts/nga_ok.html,长度:", len(body2))
    # 简单检查是否拿到帖子内容
    if "帖子" in body2 or "回复" in body2 or "UID" in body2:
        print("✅ 疑似获取到帖子内容")
    else:
        print("⚠️ 内容可疑,前 300 字符:")
        print(body2[:300])


if __name__ == "__main__":
    main()
