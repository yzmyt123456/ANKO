"""牧师章节象限识图:页按左右栏×上下两半切 4 块,逐块转录后合并。"""
import base64
import json
import sqlite3
import sys
import urllib.request
import urllib.error
from pathlib import Path

import pymupdf

PDF = "D:/bdxiazi/DND 5E 规则包/DND_5E_玩家手册CN.pdf"
PAGES = [int(x) for x in sys.argv[1].split(",") if x.strip()]
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/cleric_ocr")
OUT.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect("data/anko.db")
ai = json.loads(conn.execute("select value from system_configs where key='ai'").fetchone()[0])
conn.close()
model = "deepseek-v4-flash-vision-exp"
url = (ai.get("base_url") or "https://api.deepseek.com/v1").rstrip("/") + "/chat/completions"
prompt = (
    "请逐字转录本块全部正文(玩家手册中文版),严格自上而下。\n"
    "标题行原样输出;正文按句子断行;若有表格每行用「|」分隔单元格;\n"
    "数字、1/2、斜杠、括号、CR、伤害骰必须准确;忽略页眉页码花纹;看不清用「◻」。"
)


def _call(png: Path) -> str:
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
        "max_tokens": 6000,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + ai["api_key"]},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.loads(r.read().decode())
        return resp["choices"][0]["message"]["content"] or ""
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}"
    except Exception as exc:  # noqa: BLE001
        return f"调用失败: {exc}"


doc = pymupdf.open(PDF)
for pno in PAGES:
    out_txt = OUT / f"p{pno:03d}.txt"
    page = doc[pno]
    rect = page.rect
    quads = []
    for ci in range(2):  # 先左栏后右栏
        for yi in range(2):  # 栏内自上而下
            clip = pymupdf.Rect(
                rect.x0 + rect.width * ci / 2, rect.y0 + rect.height * yi / 2,
                rect.x0 + rect.width * (ci + 1) / 2, rect.y0 + rect.height * (yi + 1) / 2,
            )
            qpng = OUT / f"p{pno:03d}_q{ci}{yi}.png"
            pix = page.get_pixmap(dpi=200, clip=clip)
            pix.save(str(qpng))
            res = _call(qpng)
            print(f"p{pno} q{ci}{yi} ({len(res)}字)")
            quads.append(res)
    out_txt.write_text("\n\n".join(quads), encoding="utf-8")
    print(f"已合并 p{pno}.txt 总 {sum(len(x) for x in quads)}字")
doc.close()
print("完成")
