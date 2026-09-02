"""本地视觉模型(qwen2.5vl:7b)抽查武僧表图关键行,与知识卡 JSON 对照。"""
import base64
import json
import urllib.request
from pathlib import Path

IMG = Path("anko/static/img/kb/class_monk_table.png")
URL = "http://127.0.0.1:11434/api/generate"

b64 = base64.b64encode(IMG.read_bytes()).decode()
prompt = (
    "这是 DND 玩家手册中『武僧 Monk』职业等级表的截图。请只读表格内容,不要发挥:"
    "1) 第 1、4、8、9、16、19、20 行的『职业特性』列文字是什么?逐行列出。"
    "2) 这几行对应的『熟练加值』列数值?逐行列出。"
    "如看不清请直接说看不清,不要编造。"
)
body = json.dumps({
    "model": "qwen2.5vl:7b", "prompt": prompt,
    "images": [b64], "stream": False, "options": {"temperature": 0.1},
}).encode()
req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=300) as r:
    out = json.loads(r.read().decode()).get("response", "")
Path("data/monk_ocr.txt").write_text(out, encoding="utf-8")
print(out)

