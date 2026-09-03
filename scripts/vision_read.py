"""用 deepseek-v4-flash-vision-exp 视觉模型读取截图内容与布局。

用法: python scripts/vision_read.py [图片路径] [附加指令]
"""
import base64
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

PNG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/Users/15634/Desktop/屏幕截图 2026-09-03 130426.png")
EXTRA = sys.argv[2] if len(sys.argv) > 2 else ""
conn = sqlite3.connect("data/anko.db")
ai = json.loads(conn.execute("select value from system_configs where key='ai'").fetchone()[0])
conn.close()
model = "deepseek-v4-flash-vision-exp"
url = (ai.get("base_url") or "https://api.deepseek.com/v1").rstrip("/") + "/chat/completions"

b64 = base64.b64encode(PNG.read_bytes()).decode()
prompt = (
    "请详细识别这张截图:1) 整体是什么(页面/文档/软件/对话框);"
    "2) 按从上到下、从左到右描述整体布局与各个区域的作用;"
    "3) 尽量读出可见的标题、按钮、文字内容(中文原样输出,英文保留)。"
    "请客观描述,不要臆测画面外内容。"
)
if EXTRA:
    prompt += f"\n补充说明需求:{EXTRA}"
body = {
    "model": model,
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ],
    }],
    "temperature": 0.1,
    "max_tokens": 3000,
}
req = urllib.request.Request(
    url,
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + ai["api_key"]},
)
try:
    with urllib.request.urlopen(req, timeout=600) as r:
        resp = json.loads(r.read().decode())
    out = resp["choices"][0]["message"]["content"]
except urllib.error.HTTPError as exc:
    err = exc.read().decode(errors="replace")
    out = f"HTTP {exc.code}: {err[:800]}"
except Exception as exc:  # noqa: BLE001
    out = f"调用失败: {exc}"
Path("data/vision_out.txt").write_text(out, encoding="utf-8")
print(out)
