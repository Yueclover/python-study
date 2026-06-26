r"""
Day 17 · pydantic 数据校验入门
====================================
day16 拿到的是一堆 dict，取字段全靠 item.get("title")——拼错 key 不报错、
类型也不保证。pydantic 解决这个问题：你声明一个「模型」（像 TS interface），
它在运行时校验数据、做类型转换、字段缺失就报清楚的错。

这是通往 AI 应用的关键技能：FastAPI 的请求体、LLM 的结构化输出，全靠 pydantic。
对标前端：它 = TS 的 interface + zod 的运行时校验，合二为一。

先装（已装好）：  pip install pydantic
跑它：           python week03\day17_pydantic.py
"""

import sys
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ValidationError

sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，强制 UTF-8 才能打印 emoji/特殊符号

# ---------------------------------------------------------------------------
# 1. 定义一个模型
# ---------------------------------------------------------------------------
# JS/zod:  const Story = z.object({ id: z.number(), title: z.string() })
# TS:      interface Story { id: number; title: string }
# pydantic 把两者合并：声明即校验。

class Story(BaseModel):
    id: int
    title: str
    by: str                       # 作者
    score: int = 0                # 有默认值 → 可选字段（数据里没有就用 0）
    descendants: int = 0          # 评论数，HN 有时不返回这个字段

# 用 dict 实例化（** 解包，把 dict 变成关键字参数）
raw = {"id": 123, "title": "Hello HN", "by": "alice", "score": 240, "descendants": 30}
story = Story(**raw)              # 等价 Story.model_validate(raw)
print("✅ 校验通过：", story)
print("点属性取值（不再是 dict['key']）：", story.title, story.score)

# ---------------------------------------------------------------------------
# 2. 自动类型转换 + 校验失败的报错
# ---------------------------------------------------------------------------
# pydantic 会尽力转换："240" → 240。但转不动就报错。
coerced = Story(id="123", title="x", by="bob", score="240")   # 字符串数字自动转 int
print("\n字符串 '123' 被转成：", repr(coerced.id), type(coerced.id).__name__)

# 缺字段 / 类型彻底不对 → 抛 ValidationError，信息很清楚
try:
    Story(id="not-a-number", title="x")   # id 转不了 int，且缺 by
except ValidationError as e:
    print("\n❌ 校验失败（这正是我们要的——脏数据当场暴露）：")
    print(e)

# ---------------------------------------------------------------------------
# 3. Field：默认值、别名、约束
# ---------------------------------------------------------------------------
class StoryV2(BaseModel):
    id: int
    title: str
    by: str = "unknown"
    score: int = Field(default=0, ge=0)          # ge=0：必须 >= 0（约束校验）
    url: str | None = None                         # 可能没有 url（Ask HN 帖子就没有）
    # alias：API 字段名和你想用的属性名不一致时映射
    # 比如 API 返回 "time"（Unix 秒），你想叫 created_at
    time: int = Field(default=0, alias="time")

print("\nStoryV2 默认值：", StoryV2(id=1, title="t"))

# ---------------------------------------------------------------------------
# 4. 自定义校验 / 派生字段：field_validator
# ---------------------------------------------------------------------------
# HN 的 time 是 Unix 时间戳（秒）。我们想要可读时间。
class HNItem(BaseModel):
    id: int
    title: str = "(无标题)"
    by: str = "unknown"
    score: int = 0
    url: str | None = None
    time: int = 0
    descendants: int = 0

    @property                       # 计算属性（不存储，访问时算）——对应 JS 的 getter
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self.time) if self.time else datetime.min

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        # 校验器：返回值会替换原值。这里把空标题兜底。
        return v.strip() or "(无标题)"

hn = HNItem(id=1, title="  GrapheneOS ported  ", by="x", score=648, time=1700000000)
print("\nHNItem：")
print("  清洗后的标题：", repr(hn.title))    # 两端空格被 strip
print("  可读时间：", hn.created_at)

# ---------------------------------------------------------------------------
# 5. 模型 → dict / JSON（序列化，存缓存时用）
# ---------------------------------------------------------------------------
print("\n转 dict：", hn.model_dump())                       # → 普通 dict
print("转 JSON：", hn.model_dump_json(indent=2)[:60], "...")  # → JSON 字符串

# 反过来：JSON 字符串 → 模型
restored = HNItem.model_validate_json(hn.model_dump_json())
print("从 JSON 还原：", restored.title)

# ---------------------------------------------------------------------------
# 6. 嵌套 & 列表模型（项目会用：一批 story）
# ---------------------------------------------------------------------------
class StoryList(BaseModel):
    fetched_at: int = 0
    stories: list[HNItem] = []     # 列表里每个元素都会被校验成 HNItem

batch = StoryList(stories=[
    {"id": 1, "title": "A", "score": 100},
    {"id": 2, "title": "B", "score": 50},
])
print("\n嵌套列表模型，第一条：", batch.stories[0].title, batch.stories[0].score)

# ---------------------------------------------------------------------------
# 练习
# ---------------------------------------------------------------------------
# 1) 给 HNItem 加一个 type 字段（HN 有 "story"/"job"/"comment"），默认 "story"。
# 2) 写一个校验器：score 为负时强制改成 0（用 field_validator）。
# 3) 拿 day16 真实拉到的 dict，喂给 HNItem(**item)，看能不能直接建模成功。

if __name__ == "__main__":
    print("\n✅ day17 跑通。三件套（文件/requests/pydantic）齐了，day18 开始拼项目！")
