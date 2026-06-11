"""
第 1 周 Day 4 — 条件 if/elif/else 与循环 for/while

运行：python week01\\day04_control_flow.py
重点：Python 用缩进（4 空格）表示代码块，没有 {}。
"""

# ============================================================
# 1. 条件判断 —— elif 是 else if 的缩写
# ============================================================
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:        # 注意是 elif，不是 else if
    grade = "B"
elif score >= 60:
    grade = "C"
else:
    grade = "D"
print("成绩等级:", grade)

# 逻辑运算用单词，不是符号
age = 25
if age >= 18 and age < 60:        # and 对应 &&
    print("成年人")
if not (age > 60):                # not 对应 !
    print("未到退休年龄")

# Python 特有：链式比较（JS 不能这样写）
if 18 <= age < 60:
    print("用链式比较更简洁")

# 三元表达式（对应 cond ? a : b）
status = "及格" if score >= 60 else "不及格"
print(status)

# 👉 试一试：把 score 改成 55，重新运行看 grade 变成什么


# ============================================================
# 2. for 循环 —— Python 的 for x in 遍历「值」,等价于 JS 的 for...of
#    ⚠️ 注意:它用 in 关键字,但行为是 for...of,不是 JS 那个遍历索引的 for...in
# ============================================================
# range(n) 生成 0 到 n-1 的数字序列
for i in range(5):
    print("i =", i)          # 0 1 2 3 4

# range(start, stop, step)
for i in range(2, 11, 2):
    print("偶数:", i)        # 2 4 6 8 10

# 遍历列表
for fruit in ["苹果", "香蕉"]:
    print("吃", fruit)

# 👉 试一试：用 range 打印 1 到 10 的累加和（提示：用一个变量 total 累加）
total = 0
for i in range(1,10):
    total += i
print(f"1 到 10 的累加和是 {total}")

# ============================================================
# 3. while 循环
# ============================================================
count = 3
while count > 0:
    print("倒计时:", count)
    count -= 1               # 对应 count--，Python 没有 --
print("发射！")

# break 和 continue（和 JS 一样）
for n in range(10):
    if n == 3:
        continue            # 跳过本次
    if n == 6:
        break               # 提前结束
    print("n =", n)         # 0 1 2 4 5

# 👉 试一试：写一个 while 循环，从 10 倒数到 1
i = 10
while i > 0:
    print(i)
    i -= 1


# ============================================================
# 4. 综合小练习：FizzBuzz（经典面试题）
# ============================================================
for i in range(1, 16):
    if i % 15 == 0:
        print("FizzBuzz")
    elif i % 3 == 0:
        print("Fizz")
    elif i % 5 == 0:
        print("Buzz")
    else:
        print(i)


print("\n[完成] Day 4 跑通了！去 ROADMAP.md 勾掉 Day 4。")
