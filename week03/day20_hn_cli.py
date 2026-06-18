r"""
Day 20 · 🛠️ 项目③ — 并发拉取 + argparse 命令行
================================================
收尾。三件事：
  1) 并发拉取：day18 串行拉 30 条要十几秒，用线程池压到 1~2 秒
  2) 过滤/排序：纯函数 filter_stories（day21 重点测它）
  3) argparse：把脚本变成真正的命令行工具，支持 --top / --min-score / --save

用法示例：
    python week03\day20_hn_cli.py --top 10
    python week03\day20_hn_cli.py --top 30 --min-score 300 --save
    python week03\day20_hn_cli.py --top 15 --no-cache

这是「不查语法写出 100+ 行、带函数、能调 API 的脚本」——本周通关目标。
"""

import sys
import argparse
import time
from concurrent.futures import ThreadPoolExecutor

import requests

sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，强制 UTF-8 才能打印 emoji/特殊符号

# 复用前两天的成果
from day18_hn_models import Story, fetch_top_ids, fetch_story
from day19_hn_cache_format import format_story, save_cache, load_cache


# ---------------------------------------------------------------------------
# 1. 并发拉取：requests 是同步的，但用线程池可以同时发很多请求
# ---------------------------------------------------------------------------
# JS 里你会写 await Promise.all(ids.map(fetchOne))。
# Python 这里用 ThreadPoolExecutor —— I/O 等待型任务（网络）正适合多线程。
def fetch_stories_concurrent(limit: int = 10, workers: int = 16) -> list[Story]:
    """并发拉前 limit 条热门故事。workers 是同时进行的请求数。"""
    with requests.Session() as session:
        session.headers.update({"User-Agent": "hn-reader/1.0"})
        ids = fetch_top_ids(session, limit)

        # executor.map(func, iterable)：把每个 id 丢给线程池并发执行，
        # 返回的结果顺序和输入一致（对应 Promise.all 保持顺序）。
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = pool.map(lambda sid: fetch_story(session, sid), ids)

        # 过滤掉拉失败/已删除的 None
        return [s for s in results if s is not None]


# ---------------------------------------------------------------------------
# 2. 纯逻辑：过滤 + 排序（不碰网络/文件 → day21 用 pytest 测这个）
# ---------------------------------------------------------------------------
def filter_stories(
    stories: list[Story],
    min_score: int = 0,
    sort_by: str = "score",
) -> list[Story]:
    """按最低分过滤，再按 score 或 comments 排序。纯函数：同输入必同输出。"""
    kept = [s for s in stories if s.score >= min_score]

    if sort_by == "comments":
        kept.sort(key=lambda s: s.descendants, reverse=True)
    else:  # 默认按分数
        kept.sort(key=lambda s: s.score, reverse=True)
    return kept


# ---------------------------------------------------------------------------
# 3. 数据入口：缓存优先（复用 day19），缓存未命中才并发拉
# ---------------------------------------------------------------------------
def get_stories(limit: int, use_cache: bool = True) -> list[Story]:
    if use_cache:
        cached = load_cache()
        if cached is not None:
            return cached[:limit]
    stories = fetch_stories_concurrent(limit)
    save_cache(stories)
    return stories


# ---------------------------------------------------------------------------
# 4. argparse：定义命令行参数（标准库，比手撸 sys.argv 强太多）
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Hacker News 命令行阅读器",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,  # --help 里显示默认值
    )
    p.add_argument("--top", type=int, default=10, help="拉取并显示前 N 条热门")
    p.add_argument("--min-score", type=int, default=0, help="只显示分数 >= 此值的")
    p.add_argument("--sort", choices=["score", "comments"], default="score", help="排序依据")
    # action="store_true"：写了 --save 就是 True，不写就是 False（布尔开关）
    p.add_argument("--save", action="store_true", help="把结果另存为 hn_top.json")
    p.add_argument("--no-cache", action="store_true", help="忽略缓存，强制重新拉")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)   # argv=None 时自动读 sys.argv

    t0 = time.time()
    stories = get_stories(args.top, use_cache=not args.no_cache)
    stories = filter_stories(stories, min_score=args.min_score, sort_by=args.sort)
    elapsed = time.time() - t0

    print(f"\n=== HN 热门（{len(stories)} 条，{elapsed:.2f}s）===\n")
    for i, s in enumerate(stories, start=1):
        print(f"{i:>2}. {format_story(s)}")
        print()

    if args.save:
        out = __import__("pathlib").Path(__file__).parent / "hn_top.json"
        import json
        with open(out, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in stories], f, ensure_ascii=False, indent=2)
        print(f"💾 已保存到 {out.name}")


# ---------------------------------------------------------------------------
# 5. 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# 练习
# ---------------------------------------------------------------------------
# 1) 加一个 --author NAME 参数，只显示某作者的帖子（改 filter_stories）。
# 2) 把 workers 也做成命令行参数 --workers，对比 1 和 16 的耗时差。
# 3) 进阶：用 day13 学的 asyncio + httpx 重写 fetch_stories_concurrent，对比写法。
