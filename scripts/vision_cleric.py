"""牧师章节识图重读:渲染指定 PDF 页 → deepseek 视觉逐字转录。
用法: python scripts/vision_cleric.py <zero_index_pno> [输出目录]
"""
import base64
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

import pymupdf

PDF = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"
RAW = sys.argv[1]
if RAW == "all":
    PAGES = [55, 56, 57, 58, 60, 61, 62]
else:
    PAGES = [int(x) for x in RAW.split(",") if x.strip()]
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/cleric_ocr")
OUT.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect("data/anko.db")
ai = json.loads(conn.execute("select value from system_configs where key='ai'").fetchone()[0])
conn.close()
model = "deepseek-v4-flash-vision-exp"
url = (ai.get("base_url") or "https://api.deepseek.com/v1").rstrip("/") + "/chat/completions"
prompt = (
    "请逐字转录本页全部正文(玩家手册中文版),严格按栏自上而下、先左栏后右栏。\n"
    "规则:标题行(含中文+英文)原样输出;正文按句子断行;表格每行用「|」分隔单元格,表头行前加「表:」;\n"
    "数字、1/2、斜杠、括号、CR、伤害骰必须准确;忽略页眉页码与花纹;看不清用「◻」。"
)


def _vision(ai: dict, png: Path, out_dir: Path, pno: int) -> None:
    b64 = base64.b64encode(png.read_bytes()).decode()
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
        "max_tokens": 16000,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + ai["api_key"]},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            resp = json.loads(r.read().decode())
        out = resp["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        out = f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:800]}"
    except Exception as exc:  # noqa: BLE001
        out = f"调用失败: {exc}"
    out_dir.joinpath(f"p{pno:03d}.txt").write_text(out, encoding="utf-8")
    print(f"已写 p{pno:03d}.txt ({len(out)}字)\n{'='*20}\n{out[:900]}")

# 顺序执行:每页一图一次视觉转录,跳过已读页
doc = pymupdf.open(PDF)
for PNO in PAGES:
    txt = OUT / f"p{PNO:03d}.txt"
    if txt.exists() and txt.stat().st_size > 50:
        print("跳过已读", txt)
        continue
    png = OUT / f"p{PNO:03d}.png"
    pix = doc[PNO].get_pixmap(dpi=220)
    pix.save(str(png))
    _vision(ai, png, OUT, PNO)
doc.close()
print("完成")
