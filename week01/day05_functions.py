"""
第 1 周 Day 5 — 函数 def、参数、返回值

运行：python week01\\day05_functions.py
"""

# ============================================================
# 1. 定义函数 —— def 代替 function
# ============================================================
def greet(name):
    return f"你好，{name}！"

print(greet("小明"))

# 带类型注解（你写过 TS 会很熟，AI 库全靠它）
def add(a: int, b: int) -> int:
    return a + b

print(add(3, 5))

# 👉 试一试：写一个函数 square(n) 返回 n 的平方
def square(n): 
    return n ** 2

print(square(5))              # 25，用默认 exp=2


# ============================================================
# 2. 默认参数（对应 JS 的默认参数）
# ============================================================
def power(base, exp=2):       # exp 默认是 2
    return base ** exp

print(power(5))               # 25，用默认 exp=2
print(power(5, 3))            # 125

# 关键字参数 —— 调用时指定参数名，可乱序（JS 没有）
def create_user(name, age, city="未知"):
    return f"{name}, {age}岁, 来自{city}"

print(create_user(age=28, name="小红", city="北京"))

# 👉 试一试：调用 create_user 时不传 city，看输出


# ============================================================
# 3. 多返回值 —— 其实是返回元组（JS 要返回数组或对象）
# ============================================================
def min_max(nums):
    return min(nums), max(nums)

low, high = min_max([3, 1, 9, 5])   # 解构接收
print(f"最小 {low}, 最大 {high}")

# 👉 试一试：写一个函数返回一个列表的「和」与「平均值」


# ============================================================
# 4. *args 和 **kwargs —— 接收任意数量参数
# ============================================================
def total(*nums):             # *nums 收集所有位置参数成元组
    return sum(nums)

print(total(1, 2, 3, 4))      # 10，类似 JS 的 ...rest

def describe(**info):         # **info 收集所有关键字参数成字典
    for key, value in info.items():
        print(f"{key}: {value}")

describe(name="小明", age=28, job="前端")

# 👉 试一试：用 *args 写一个函数，返回所有传入数字里最大的


# ============================================================
# 5. lambda —— 匿名函数（对应箭头函数，但只能写一行）
# ============================================================
double = lambda x: x * 2      # 对应 const double = x => x * 2
print(double(10))             # 20

# 常用于排序的 key
people = [("小明", 28), ("小红", 22), ("小刚", 35)]
people.sort(key=lambda p: p[1])    # 按年龄（元组第 2 项）排序
print(people)

# 👉 试一试：把 people 改成按名字排序（提示：key=lambda p: p[0]）


# ============================================================
# 6. 文档字符串 docstring —— 写在函数第一行的说明
# ============================================================
def bmi(weight, height):
    """计算 BMI 指数。这段三引号说明就是 docstring。"""
    return weight / (height ** 2)

print(bmi.__doc__)            # 可以读取说明


print("\n[完成] Day 5 跑通了！去 ROADMAP.md 勾掉 Day 5。")
