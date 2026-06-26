r"""
Day 18 · 🛠️ 项目① — 建模 + 拉数据
====================================
正式开做 Hacker News 阅读器。今天的目标：
  把 day16(requests) + day17(pydantic) 拼起来，
  拉到「前 N 条热门故事」并打印成结构化对象。

数据流（今天只做前半段）：
  topstories.json → 拿到 ID 列表 → 逐条拉详情 → pydantic 校验成 Story → 打印

跑它：  python week03\day18_hn_models.py
"""

import sys
import requests
from pydantic import BaseModel, field_validator

sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，强制 UTF-8 才能打印 emoji/特殊符号

HN = "https://hacker-news.firebaseio.com/v0"


# ---------------------------------------------------------------------------
# 1. 数据模型（day17 的成果，精简成项目够用的版本）
# ---------------------------------------------------------------------------
class Story(BaseModel):
    id: int
    title: str = "(无标题)"
    by: str = "unknown"          # 作者
    score: int = 0               # 分数
    url: str | None = None       # Ask HN 类帖子没有外链
    time: int = 0                # Unix 时间戳（秒）
    descendants: int = 0         # 评论数

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        return v.strip() or "(无标题)"


# ---------------------------------------------------------------------------
# 2. 数据获取层：每个函数只干一件事（好测试、好复用）
# ---------------------------------------------------------------------------
def fetch_top_ids(session: requests.Session, limit: int = 10) -> list[int]:
    """拉热门故事的 ID 列表，只取前 limit 个。"""
    r = session.get(f"{HN}/topstories.json", timeout=10)
    r.raise_for_status()
    return r.json()[:limit]      # 切片：API 返回 500 个，我们只要前面几个


def fetch_story(session: requests.Session, story_id: int) -> Story | None:
    """拉单条详情并校验成 Story。失败/已删除返回 None。"""
    try:
        r = session.get(f"{HN}/item/{story_id}.json", timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:             # 已删除的 item 会返回 null → Python 的 None
            return None
        return Story(**data)     # ← dict 解包喂给 pydantic，这一步就是「校验+建模」
    except requests.RequestException as e:
        print(f"  ⚠️ 拉取 {story_id} 失败：{e}")
        return None


def fetch_top_stories(limit: int = 10) -> list[Story]:
    """组合上面两个函数：拿 ID 列表 → 逐条拉详情。今天先用最朴素的串行循环。"""
    with requests.Session() as session:
        session.headers.update({"User-Agent": "hn-reader/0.1"})
        ids = fetch_top_ids(session, limit)
        print(f"拿到 {len(ids)} 个热门 ID，开始逐条拉取（串行，会有点慢）...")

        stories: list[Story] = []
        for i, sid in enumerate(ids, start=1):
            story = fetch_story(session, sid)
            if story:                       # 过滤掉拉失败的 None
                stories.append(story)
                print(f"  [{i}/{len(ids)}] ✓ {story.title[:50]}")
        return stories


# ---------------------------------------------------------------------------
# 3. 跑起来看看
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    stories = fetch_top_stories(limit=8)

    # 按分数从高到低排序（sorted + lambda，对应 JS 的 arr.sort((a,b)=>b.score-a.score)）
    stories.sort(key=lambda s: s.score, reverse=True)

    print("\n=== 按分数排序 ===")
    for s in stories:
        # f-string 对齐：:>4 右对齐占 4 格，让分数成列
        print(f"  {s.score:>4} 分 | {s.title}")
        print(f"           by {s.by} · {s.descendants} 评论 · {s.url or '(无外链)'}")

    print(f"\n✅ day18 跑通，拉到 {len(stories)} 条。")
    print("   注意到串行拉 8 条要等好几秒了吗？day20 会用并发把它压到 1 秒内。")

# ---------------------------------------------------------------------------
# 练习
# ---------------------------------------------------------------------------
# 1) 给 fetch_top_stories 加个参数，支持换成 "newstories"（最新）或 "askstories"。
# 2) 统计这批故事的平均分（sum(...)/len(...)），打印出来。
# 3) 思考：现在拉 30 条会很慢，慢在哪？（提示：每次 get 都在干等网络）
