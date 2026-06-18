r"""
Day 21 · 给项目写 pytest 测试
====================================
这是测试文件本体。pytest 的约定：文件名 test_*.py、函数名 test_*，
pytest 自动发现并运行。对应前端的 jest/vitest。

只测「纯函数」和「模型」——它们不碰网络，给定输入必得固定输出，所以测试稳定、秒级。
（拉网络的函数怎么测？见 day21_review.py 讲的 mock 思路。）

运行（在项目根目录）：
    pytest week03\test_day20.py -v
    或直接 pytest（自动发现所有 test_*.py）
"""

import pytest

from day18_hn_models import Story
from day19_hn_cache_format import time_ago, score_badge, format_story
from day20_hn_cli import filter_stories


# ---------------------------------------------------------------------------
# 1. 测纯函数 time_ago —— 注入固定的 now，结果就完全可预测
# ---------------------------------------------------------------------------
def test_time_ago_just_now():
    assert time_ago(1000, now=1030) == "刚刚"        # 30 秒 < 1 分钟

def test_time_ago_minutes():
    assert time_ago(1000, now=1000 + 5 * 60) == "5 分钟前"

def test_time_ago_hours():
    # 注意：起点不能用 0——0 会被 time_ago 当成「没有时间戳」。用一个非零基准。
    base = 1_700_000_000
    assert time_ago(base, now=base + 3 * 3600) == "3 小时前"

def test_time_ago_days():
    base = 1_700_000_000
    assert time_ago(base, now=base + 2 * 86400) == "2 天前"

def test_time_ago_zero_is_unknown():
    assert time_ago(0, now=12345) == "未知时间"      # 没有时间戳的兜底（timestamp=0）


# ---------------------------------------------------------------------------
# 2. 参数化测试：一个函数测多组数据（对应 jest 的 test.each）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("score, expected", [
    (500, "🔥"),
    (300, "🔥"),    # 边界：恰好 300
    (299, "⭐"),    # 边界：差一分
    (100, "⭐"),
    (99, "  "),
    (0, "  "),
])
def test_score_badge(score, expected):
    assert score_badge(score) == expected


# ---------------------------------------------------------------------------
# 3. 测模型：pydantic 校验器和默认值
# ---------------------------------------------------------------------------
def test_story_defaults():
    s = Story(id=1)                       # 只给必填的 id，其余走默认
    assert s.title == "(无标题)"
    assert s.score == 0
    assert s.url is None

def test_story_title_is_trimmed():
    s = Story(id=1, title="  有空格  ")    # 校验器应 strip
    assert s.title == "有空格"

def test_story_coerces_string_number():
    s = Story(id=1, score="240")          # pydantic 把 "240" 转成 int
    assert s.score == 240
    assert isinstance(s.score, int)


# ---------------------------------------------------------------------------
# 4. 测过滤/排序逻辑（项目核心业务逻辑，最该测）
# ---------------------------------------------------------------------------
@pytest.fixture                            # fixture：可复用的测试数据，多个测试共享
def sample_stories():
    return [
        Story(id=1, title="A", score=50, descendants=10),
        Story(id=2, title="B", score=300, descendants=5),
        Story(id=3, title="C", score=120, descendants=99),
    ]

def test_filter_by_min_score(sample_stories):
    kept = filter_stories(sample_stories, min_score=100)
    assert len(kept) == 2                  # 只剩 300 和 120 的
    assert all(s.score >= 100 for s in kept)

def test_sort_by_score_desc(sample_stories):
    kept = filter_stories(sample_stories, sort_by="score")
    scores = [s.score for s in kept]
    assert scores == [300, 120, 50]        # 从高到低

def test_sort_by_comments(sample_stories):
    kept = filter_stories(sample_stories, sort_by="comments")
    assert kept[0].id == 3                 # 评论数 99 的排第一

def test_filter_empty_input():
    assert filter_stories([], min_score=100) == []   # 边界：空输入不崩


# ---------------------------------------------------------------------------
# 5. 测组合输出 format_story（断言关键内容在里面，不死磕整段字符串）
# ---------------------------------------------------------------------------
def test_format_story_contains_title_and_author():
    s = Story(id=1, title="GrapheneOS", by="alice", score=648, descendants=284, time=0)
    out = format_story(s, now=3600)        # now 固定，time_ago 才稳定
    assert "GrapheneOS" in out
    assert "alice" in out
    assert "648" in out
    assert "284 评论" in out


# ---------------------------------------------------------------------------
# 练习
# ---------------------------------------------------------------------------
# 1) 给 filter_stories 的 --author 练习功能补一个测试（先实现再测，或先测后实现=TDD）。
# 2) 用 pytest.raises 测「给 Story 传 id='abc' 会抛 ValidationError」。
#    提示：
#        from pydantic import ValidationError
#        with pytest.raises(ValidationError):
#            Story(id="abc")
