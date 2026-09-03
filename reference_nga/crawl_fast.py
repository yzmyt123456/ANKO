# -*- coding: utf-8 -*-
"""crawl_nga.py 的并发+keep-alive 加速版(同一目录、共用 out/)。"""
from __future__ import annotations

import http.client
import json
import os
import sys
import threading
import time

import crawl_nga

TID = crawl_nga.TID
LAST_PAGE = crawl_nga.LAST_PAGE
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = crawl_nga.OUT
COOKIE = open(crawl_nga.COOKIE_FILE, encoding="utf-8").read().strip()
WORKERS = int(os.environ.get("NGA_WORKERS", "6"))
lock = threading.Lock()


def fetch_page_fast(page: int, holder: dict) -> str:
    return crawl_nga.fetch_page(COOKIE, page)


def worker(chunk: list[int], out_fp: str, success: list[int], err: list[tuple[int, str]]) -> None:
    holder: dict = {"conn": None}
    local = threading.local()
    local.buf: list[str] = []
    for page in chunk:
        try:
            html = fetch_page_fast(page, holder)
            posts = crawl_nga.parse_page(page, html)
            with lock:
                with open(out_fp, "a", encoding="utf-8") as f:
                    for p in posts:
                        f.write(json.dumps(p, ensure_ascii=False) + "\n")
                success.append(page)
        except Exception as e:
            err.append((page, str(e)))
        time.sleep(0.12)


def main() -> None:
    start = 1
    done = crawl_nga.load_done()
    todo = [p for p in range(start, LAST_PAGE + 1) if p not in done]
    if not todo:
        print("nothing to do")
        return
    size = (len(todo) + WORKERS - 1) // WORKERS
    chunks = [todo[i:i + size] for i in range(0, len(todo), size)]
    out_fp = os.path.join(OUT, "op_posts.jsonl")
    success: list[int] = []
    err: list[tuple[int, str]] = []
    threads = []
    t0 = time.time()
    for c in chunks:
        if not c:
            continue
        t = threading.Thread(target=worker, args=(c, out_fp, success, err), daemon=True)
        t.start()
        threads.append(t)
    while any(t.is_alive() for t in threads):
        elapsed = int(time.time() - t0)
        print(f"todo={len(todo)} done={len(success)} err={len(err)} elapsed={elapsed}s", flush=True)
        time.sleep(8)
    for t in threads:
        t.join()
    done |= set(success)
    with open(os.path.join(OUT, "done_pages.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(map(str, sorted(done))) + "\n")
    with open(os.path.join(OUT, "errors.txt"), "a", encoding="utf-8") as f:
        for page, msg in err:
            f.write(f"{page}\t{msg}\n")
    print(f"FINISH todo={len(todo)} ok={len(success)} err={len(err)} total={int(time.time()-t0)}s")


if __name__ == "__main__":
    main()
