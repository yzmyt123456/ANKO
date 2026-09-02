"""通过 GitHub Git Data API 推送本地提交(在 github.com 主站不可达时的备用通道)。

用法:
  python scripts/push_via_api.py [--base <本地基线commit>]

--base 用于本地仓库缺少远程 commit 对象的情况(例如远程经 API 推送生成
了不同 sha 的等价提交):提供"内容与远程当前 main 相同"的本地 commit,
脚本将据此计算差异。
"""

from __future__ import annotations

import argparse
import base64
import os
import subprocess
import sys

import httpx

TOKEN = os.environ.get("ANKO_GH_TOKEN")
REPO = "yzmyt123456/ANKO"
if not TOKEN:
    print("请设置环境变量 ANKO_GH_TOKEN")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "anko-cli",
    "Accept": "application/vnd.github+json",
}
API = f"https://api.github.com/repos/{REPO}"
GIT = f"{API}/git"


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], text=True, encoding="utf-8", errors="replace"
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None, help="本地基线 commit(可选)")
    args = parser.parse_args()

    head = git("rev-parse", "HEAD")
    message = git("log", "-1", "--format=%B", head).strip()

    # 1. 获取远程 main 当前 commit 与 tree
    branch_resp = httpx.get(f"{API}/branches/main", headers=HEADERS, timeout=30)
    branch_resp.raise_for_status()
    remote_sha = branch_resp.json()["commit"]["sha"]
    base_tree = httpx.get(
        f"{GIT}/commits/{remote_sha}", headers=HEADERS, timeout=30
    ).json()["tree"]["sha"]
    print(f"本地 HEAD:   {head}")
    print(f"远程 main:   {remote_sha}")
    print(f"远程 tree:   {base_tree}")

    # 2. 计算差异(用 --base 或 origin/main 作为基线)
    base = args.base or git("rev-parse", "origin/main")
    diff = subprocess.check_output(
        ["git", "diff", "--name-status", base, head],
        text=True,
        encoding="utf-8",
        errors="replace",
    ).splitlines()
    print(f"基线 commit: {base}({len(diff)} 个文件变更)")

    # 3. 上传变更文件的 blob
    entries = []
    for line in diff:
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        if status == "D":
            continue
        with open(path, "rb") as f:
            raw = f.read()
        blob_resp = httpx.post(
            f"{GIT}/blobs",
            headers=HEADERS,
            json={
                "content": base64.b64encode(raw).decode(),
                "encoding": "base64",
            },
            timeout=60,
        )
        blob_resp.raise_for_status()
        entries.append(
            {
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_resp.json()["sha"],
            }
        )
        print(f"  · blob: {path}")

    # 4. 创建 tree(基于远程当前树)
    tree_resp = httpx.post(
        f"{GIT}/trees",
        headers=HEADERS,
        json={"base_tree": base_tree, "tree": entries},
        timeout=30,
    )
    tree_resp.raise_for_status()
    tree_sha = tree_resp.json()["sha"]
    print(f"  · tree: {tree_sha}")

    # 5. 创建 commit
    commit_resp = httpx.post(
        f"{GIT}/commits",
        headers=HEADERS,
        json={"message": message, "tree": tree_sha, "parents": [remote_sha]},
        timeout=30,
    )
    commit_resp.raise_for_status()
    commit_sha = commit_resp.json()["sha"]
    print(f"  · commit: {commit_sha}")

    # 6. 更新 main 引用
    ref_resp = httpx.patch(
        f"{API}/git/refs/heads/main",
        headers=HEADERS,
        json={"sha": commit_sha, "force": False},
        timeout=30,
    )
    ref_resp.raise_for_status()
    print(f"✅ 已通过 API 推送 main → {commit_sha}")


if __name__ == "__main__":
    main()
