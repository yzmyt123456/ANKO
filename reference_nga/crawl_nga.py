# -*- coding: utf-8 -*-
"""抓取 NGA 安科帖并抽取指定楼主(uid)的全部楼层/热门评论。

用法:
    python crawl_nga.py <start> <end>            # 分页抓取 [start,end]
    python crawl_nga.py 1 3 --test               # 测试:打印楼主发言摘要

Cookie 从同目录 cookie.txt 读取(不进入 git)。
输出 out/op_posts.jsonl,已成功的页码记录在 out/done_pages.txt,断点续跑。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
COOKIE_FILE = os.path.join(HERE, "cookie.txt")
TID = 46321088
TARGET_UID = "63740536"  # 楼主
LAST_PAGE = 747
DELAY = 0.35


def headers(cookie: str, referer: str | None = None) -> dict[str, str]:
    h = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Connection": "keep-alive",
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0",
        "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Microsoft Edge";v="152"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        h["Referer"] = referer
    return h


def fetch_page(cookie: str, page: int) -> str:
    url = f"https://ngabbs.com/read.php?tid={TID}&page={page}"
    referer = f"https://ngabbs.com/read.php?tid={TID}&page={max(page - 1, 1)}"
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers(cookie, referer))
            raw = urllib.request.urlopen(req, timeout=30).read()
            html = raw.decode("gbk", errors="replace")
            if "postliststart" not in html and "forumbox postbox" not in html:
                raise RuntimeError("页面不含帖子列表(可能被风控/跳登录)")
            return html
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"page {page} failed: {last_err}")


def balanced_span(html: str, start: int) -> tuple[str, int]:
    depth = 1
    i = start
    n = len(html)
    while i < n:
        nxt_o = html.find("<span", i, i + 20)
        nxt_c = html.find("</span>", i)
        if nxt_o != -1 and (nxt_c == -1 or nxt_o < nxt_c):
            depth += 1
            i = nxt_o + 5
        elif nxt_c != -1:
            depth -= 1
            if depth == 0:
                return html[start:nxt_c], nxt_c
            i = nxt_c + 7
        else:
            return html[start:], n
    return html[start:], n


def extract_post_content(html: str, idx: str) -> str:
    key = f"id='postcontent{idx}' class='postcontent ubbcode'>"
    p = html.find(key)
    if p == -1:
        return ""
    return balanced_span(html, p + len(key))[0]


def extract_comment_content(html: str, cid: str) -> str:
    key = f"id='postcomment__{cid}'>"
    p = html.find(key)
    if p == -1:
        return ""
    return balanced_span(html, p + len(key))[0]


def parse_page(page: int, html: str) -> list[dict]:
    rows: list[dict] = []
    floor_re = re.compile(
        r"<a href='nuke\.php\?func=ucp&uid=(\d+)' id='postauthor(\d+)' class='author b'>"
    )
    ms = list(floor_re.finditer(html))
    for m in ms:
        uid, idx = m.group(1), m.group(2)
        if uid != TARGET_UID:
            continue
        seg_start = m.start()
        nxt = next((x.start() for x in ms if x.start() > seg_start), -1)
        seg_end = nxt if nxt != -1 else html.find("<!--postlistend-->")
        if seg_end == -1:
            seg_end = seg_start + 200000
        seg = html[seg_start:seg_end]
        date_m = re.search(rf"id='postdate{idx}' title='reply time'>([^<]*)<", seg)
        subj_m = re.search(rf"<h3 id='postsubject{idx}'>(.*?)</h3>", seg, re.S)
        content = extract_post_content(html, idx).strip()
        if not content:
            continue
        rows.append({
            "kind": "floor",
            "page": page,
            "floor": int(idx),
            "author": uid,
            "date": date_m.group(1).strip() if date_m else "",
            "subject": subj_m.group(1).strip() if subj_m else "",
            "content": content,
        })
    c_re = re.compile(
        r"id='commentauthor__(?P<cid>\d+)' class='author b onbr'>UID:(?P<uid>\d+)"
    )
    seen: set[str] = set()
    for m in c_re.finditer(html):
        cid, uid = m.group("cid"), m.group("uid")
        if uid != TARGET_UID or cid in seen:
            continue
        seen.add(cid)
        seg = html[max(0, m.start() - 300): m.start() + 20000]
        date_m = re.search(r"title='reply time'>([^<]*)<", seg)
        content = extract_comment_content(html, cid).strip()
        if content:
            rows.append({
                "kind": "comment",
                "page": page,
                "floor": -1,
                "comment_id": int(cid),
                "author": uid,
                "date": date_m.group(1).strip() if date_m else "",
                "content": content,
            })
    return rows


def load_done() -> set[int]:
    fp = os.path.join(OUT, "done_pages.txt")
    if not os.path.exists(fp):
        return set()
    with open(fp, encoding="utf-8") as f:
        return {int(x) for x in f.read().split() if x.isdigit()}


def main() -> None:
    if not os.path.exists(COOKIE_FILE):
        sys.exit("缺少 cookie.txt")
    cookie = open(COOKIE_FILE, encoding="utf-8").read().strip()
    os.makedirs(OUT, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    test = "--test" in sys.argv
    start, end = (int(args[0]), int(args[1])) if len(args) >= 2 else (1, LAST_PAGE)
    end = min(end, LAST_PAGE)
    out_fp = os.path.join(OUT, "op_posts.jsonl")
    done = load_done()
    stats = {"pages_ok": 0, "pages_err": 0, "op_posts": 0}
    with open(out_fp, "a", encoding="utf-8") as out:
        for page in range(start, end + 1):
            if page in done:
                continue
            try:
                html = fetch_page(cookie, page)
            except Exception as e:
                stats["pages_err"] += 1
                with open(os.path.join(OUT, "errors.txt"), "a", encoding="utf-8") as ef:
                    ef.write(f"{page}\t{e}\n")
                continue
            posts = parse_page(page, html)
            for p in posts:
                out.write(json.dumps(p, ensure_ascii=False) + "\n")
            out.flush()
            done.add(page)
            with open(os.path.join(OUT, "done_pages.txt"), "w", encoding="utf-8") as df:
                df.write("\n".join(map(str, sorted(done))) + "\n")
            stats["pages_ok"] += 1
            stats["op_posts"] += len(posts)
            if test and posts:
                for p in posts:
                    print(f"--p{page} floor={p.get('floor')} {p['date']} len={len(p['content'])}")
                    print(p["content"][:220].replace("\n", " "))
            if page % 10 == 0 or page == start:
                print(f"page {page}/{end} ok={stats['pages_ok']} op={stats['op_posts']} err={stats['pages_err']}", flush=True)
            time.sleep(DELAY)
    print("DONE", stats)


if __name__ == "__main__":
    main()
