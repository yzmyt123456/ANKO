"""HTML 标签闭合校验:用 html.parser 检查 static/index.html 的标签配平。

用法: python scripts/check_html.py
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class _Checker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.errors: list[str] = []
        self.void = {"area", "base", "br", "col", "embed", "hr", "img",
                     "input", "link", "meta", "param", "source", "track", "wbr"}

    def handle_starttag(self, tag, attrs):
        if tag not in self.void:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in self.void:
            return
        if not self.stack:
            self.errors.append(f"多余闭合 </{tag}> (行 {self.getpos()[0]})")
            return
        open_tag, line = self.stack.pop()
        if open_tag != tag:
            self.errors.append(
                f"标签不匹配:第{line}行 <{open_tag}> 被 </{tag}> 闭合 (行 {self.getpos()[0]})"
            )


def main() -> None:
    path = ROOT / "anko" / "static" / "index.html"
    checker = _Checker()
    checker.feed(path.read_text(encoding="utf-8"))
    for tag, line in checker.stack:
        checker.errors.append(f"未闭合标签 <{tag}> (行 {line})")

    if checker.errors:
        print(f"❌ {len(checker.errors)} 处 HTML 问题:")
        for e in checker.errors[:20]:
            print("  -", e)
        sys.exit(1)
    print("✅ HTML 标签配平校验通过")


if __name__ == "__main__":
    main()
