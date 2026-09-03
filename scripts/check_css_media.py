"""检查 style.css 中各关键选择器是否被 tinycss2 正确解析。"""

import tinycss2

css = open("anko/static/css/style.css", encoding="utf-8").read()
rules = tinycss2.parse_stylesheet(css)
print("顶层节点数:", len(rules))

selectors = [".kb-group", ".kb-grid-list", ".kb-entry", ".kb-tab",
             ".modal", ":root", ".gen-process", ".settings-grid",
             ".dnd-stats", ".wiki-link"]
found = {s: False for s in selectors}


def scan(nodes):
    for r in nodes:
        if r.type == "qualified-rule":
            sel = tinycss2.serialize(r.prelude)
            for s in selectors:
                if s in sel:
                    found[s] = True
        elif r.type == "at-rule" and r.content:
            scan(r.content)


scan(rules)
for s, ok in found.items():
    print(f"  {s}: {'OK' if ok else 'MISSING!'}")
