"""
第 2 周 Day 12 — 类型注解 type hints（会 TS 就秒懂）

运行：python week02\\day12_type_hints.py

重点：Python 的类型注解【运行时不强制】，只是给人和工具看的。
但 FastAPI / Pydantic / AI 库全靠它工作，必须掌握。
"""
from typing import Optional, Union

# ============================================================
# 1. 基础类型注解 —— 和 TS 几乎一样，冒号语法
# ============================================================
name: str = "小明"           # 对应 TS: let name: string
age: int = 28
height: float = 1.75
is_dev: bool = True

def greet(name: str) -> str:        # 参数: 类型，-> 返回值类型
    return f"Hi {name}"

print(greet("Tom"))

# 注意：下面这行不会报错！Python 运行时不检查类型
wrong: int = "我其实是字符串"
print(wrong)                # 正常打印。类型检查靠 mypy/IDE，不靠运行时

# 👉 试一试：写一个函数 add(a: int, b: int) -> int


# ============================================================
# 2. 容器类型 —— list / dict / tuple 带元素类型
# ============================================================
# Python 3.9+ 直接用内置类型（你的是 3.13，没问题）
scores: list[int] = [88, 92, 79]                 # 对应 number[]
user: dict[str, str] = {"name": "小明"}           # 对应 Record<string,string>
point: tuple[int, int] = (3, 4)

def average(nums: list[float]) -> float:
    return sum(nums) / len(nums)

print(average([1, 2, 3]))

# 👉 试一试：写一个函数，接收 list[str]，返回拼接后的 str（用 " ".join）


# ============================================================
# 3. Optional 和 Union —— 可空 / 多类型
# ============================================================
# Optional[str] 表示「str 或 None」，对应 TS 的 string | null
def find_user(uid: int) -> Optional[str]:
    users = {1: "小明", 2: "小红"}
    return users.get(uid)               # 找不到返回 None

print(find_user(1))     # 小明
print(find_user(99))    # None

# Union 表示多种类型之一（Python 3.10+ 可写成 int | str）
def to_text(x: int | str) -> str:       # 对应 TS: number | string
    return str(x)

print(to_text(123))
print(to_text("abc"))

# 👉 试一试：写一个函数返回 Optional[int]，找不到时返回 None


# ============================================================
# 4. 给函数/类加注解的实战价值
# ============================================================
class Product:
    def __init__(self, name: str, price: float, tags: list[str]) -> None:
        self.name = name
        self.price = price
        self.tags = tags

    def discounted(self, rate: float) -> float:
        return self.price * (1 - rate)


p = Product("键盘", 299.0, ["数码", "外设"])
print(f"{p.name} 打 8 折: {p.discounted(0.2):.2f}")

# IDE 会根据注解给你自动补全和报错提示，这就是注解的最大价值。


# ============================================================
# 5. 预告：Pydantic（第 3 周 + AI 开发核心）
# ============================================================
# Pydantic 让类型注解「真正生效」——自动校验数据。
# 这是 FastAPI 和所有 LLM 结构化输出的基石，先混个眼熟：
PREVIEW = """
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

u = User(name="小明", age="28")   # "28" 会被自动转成 int 28
print(u.age)                       # 28（int）
User(name="x", age="abc")          # 直接报校验错误！
"""
print(PREVIEW)

# 👉 进阶：装好 pydantic（pip install pydantic）后，把上面 PREVIEW 的代码
#         复制到一个新文件里跑跑看，感受「类型注解真正生效」。

print("[完成] Day 12 跑通了！去 ROADMAP.md 勾掉 Day 12。")
