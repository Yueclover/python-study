"""
第 2 周 Day 10 — 上下文管理器 with + 异常处理 try/except

运行：python week02\\day10_context_exception.py
"""

# ============================================================
# 1. 异常处理 —— try/except 对应 try/catch
# ============================================================
try:
    result = 10 / 0
except ZeroDivisionError:               # 对应 catch，但能精确指定异常类型
    print("不能除以 0")

# 捕获多种异常
def parse_age(text):
    try:
        age = int(text)                 # 可能抛 ValueError
        return 100 / age                # 可能抛 ZeroDivisionError
    except ValueError:
        return "请输入数字"
    except ZeroDivisionError:
        return "年龄不能为 0"
    else:
        print("（没有异常时才执行 else）")
    finally:
        print("（finally 一定执行，常用于清理）")

print(parse_age("abc"))
print(parse_age("0"))
print(parse_age("25"))

# 👉 试一试：把 parse_age("25") 的结果打印出来，观察 else 和 finally


# ============================================================
# 2. 拿到异常对象 + 主动抛异常
# ============================================================
try:
    int("not a number")
except ValueError as e:                 # as e 拿到异常对象
    print(f"出错了: {e}")

def set_age(age):
    if age < 0:
        raise ValueError("年龄不能为负数")   # 对应 throw new Error()
    return age

try:
    set_age(-5)
except ValueError as e:
    print(f"捕获: {e}")

# 👉 试一试：写一个函数，参数不是字符串就 raise TypeError


# ============================================================
# 3. 上下文管理器 with —— 自动管理资源（JS 没有对应物）
# ============================================================
# 痛点：打开文件后必须关闭，否则泄漏。with 帮你自动关。

# 不用 with（容易忘记 close，出异常还会泄漏）：
# f = open("test.txt", "w")
# f.write("hi")
# f.close()

# 用 with（推荐）—— 代码块结束自动关闭文件，哪怕中途报错
with open("week02_temp.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n")
    f.write("第二行\n")
# 出了 with 块，文件已自动关闭

# 读回来
with open("week02_temp.txt", "r", encoding="utf-8") as f:
    content = f.read()
print("文件内容:")
print(content)

# 注意：Windows 写中文一定要 encoding="utf-8"，否则可能乱码

# 👉 试一试：用 with 打开文件，用 f.readlines() 按行读成列表


# ============================================================
# 4. 自己写一个上下文管理器（用装饰器，最简单的方式）
# ============================================================
from contextlib import contextmanager

@contextmanager
def timer_block(name):
    import time
    start = time.time()
    yield                               # yield 之前 = 进入时执行
    cost = time.time() - start          # yield 之后 = 退出时执行
    print(f"[{name}] 耗时 {cost:.4f} 秒")


with timer_block("计算任务"):
    total = sum(range(1_000_000))
print("结果:", total)

# 👉 试一试：用 with timer_block("我的任务"): 包住一段你自己的代码


# ============================================================
# 清理临时文件
# ============================================================
import os
if os.path.exists("week02_temp.txt"):
    os.remove("week02_temp.txt")

print("\n[完成] Day 10 跑通了！去 ROADMAP.md 勾掉 Day 10。")
