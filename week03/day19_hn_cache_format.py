r"""
Day 19 · 🛠️ 项目② — 本地 JSON 缓存 + 格式化输出
================================================
day18 能拉数据了，但有两个问题：
  1) 每次运行都重新拉，慢且浪费 → 加「本地 JSON 缓存」（day15 的文件 IO 派上用场）
  2) 打印太朴素 → 写「格式化」函数，把时间戳变成「3 小时前」，分数高亮

这两块都是「纯函数」（输入定、输出定、不碰网络），所以特别好测试——day21 就测它们。

跑它：  python week03\day19_hn_cache_format.py
"""

import sys
import json
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，强制 UTF-8 才能打印 emoji/特殊符号

# 复用 day18 的模型和拉取函数（同目录可以直接 import 文件名）
from day18_hn_models import Story, fetch_top_stories

CACHE_PATH = Path(__file__).parent / "hn_cache.json"
CACHE_TTL = 600   # 缓存有效期 10 分钟（秒）


# ---------------------------------------------------------------------------
# 1. 格式化：纯函数（不依赖网络/文件，给定输入必得固定输出）
# ---------------------------------------------------------------------------
def time_ago(timestamp: int, now: int | None = None) -> str:
    """Unix 秒 → '3 小时前' 这种人话。now 可注入，方便测试（不依赖真实当前时间）。"""
    if not timestamp:
        return "未知时间"
    now = now if now is not None else int(time.time())
    diff = now - timestamp
    if diff < 60:
        return "刚刚"
    if diff < 3600:
        return f"{diff // 60} 分钟前"
    if diff < 86400:
        return f"{diff // 3600} 小时前"
    return f"{diff // 86400} 天前"


def score_badge(score: int) -> str:
    """根据分数给个标记，让热门帖一眼可见。"""
    if score >= 300:
        return "🔥"
    if score >= 100:
        return "⭐"
    return "  "


def format_story(story: Story, now: int | None = None) -> str:
    """把一个 Story 渲染成两行文本。也是纯函数。"""
    head = f"{score_badge(story.score)} {story.score:>4}↑ | {story.title}"
    meta = f"        by {story.by} · {story.descendants} 评论 · {time_ago(story.time, now)}"
    return head + "\n" + meta


# ---------------------------------------------------------------------------
# 2. 缓存层：读 / 写 / 判断是否过期
# ---------------------------------------------------------------------------
def save_cache(stories: list[Story]) -> None:
    """把这批 story 连同时间戳写进 JSON 文件。"""
    payload = {
        "fetched_at": int(time.time()),
        "stories": [s.model_dump() for s in stories],   # 模型 → dict 列表
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"  💾 已缓存 {len(stories)} 条到 {CACHE_PATH.name}")


def load_cache() -> list[Story] | None:
    """读缓存。文件不存在或已过期 → 返回 None（表示「请重新拉」）。"""
    if not CACHE_PATH.exists():
        return None
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    age = int(time.time()) - payload.get("fetched_at", 0)
    if age > CACHE_TTL:
        print(f"  ⏰ 缓存已过期（{age}秒 > {CACHE_TTL}秒），需要重新拉")
        return None

    # dict 列表 → 模型列表（pydantic 再校验一遍，缓存被手改坏也能发现）
    stories = [Story(**d) for d in payload["stories"]]
    print(f"  ⚡ 命中缓存（{age}秒前），跳过网络请求")
    return stories


def get_stories(limit: int = 10, use_cache: bool = True) -> list[Story]:
    """对外的总入口：优先用缓存，没有/过期才真去拉。"""
    if use_cache:
        cached = load_cache()
        if cached is not None:
            return cached[:limit]

    stories = fetch_top_stories(limit)
    save_cache(stories)
    return stories


# ---------------------------------------------------------------------------
# 3. 跑：第一次拉网络，第二次秒回（缓存生效）
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("第一次运行（应该会拉网络）：")
    stories = get_stories(limit=8)
    stories.sort(key=lambda s: s.score, reverse=True)

    print("\n=== Hacker News 热门 ===")
    for s in stories:
        print(format_story(s))

    print("\n再调一次 get_stories（应该命中缓存，瞬间返回）：")
    get_stories(limit=8)

    print("\n✅ day19 跑通。缓存文件 hn_cache.json 已生成（.gitignore 可忽略它）。")

# ---------------------------------------------------------------------------
# 练习
# ---------------------------------------------------------------------------
# 1) time_ago 加一档「超过 30 天 → 'X 个月前'」。
# 2) 给 format_story 加个序号参数，输出 "1." "2." 这样的列表编号。
# 3) 把 CACHE_TTL 改成 5 秒，连跑两次中间手动等 6 秒，观察过期重拉。
