"""
第 1 周 Day 6 — 推导式 comprehension（Python 最爱的特性，JS 没有）

运行：python week01\\day06_comprehension.py
推导式 = 用一行写出 map/filter 的效果，非常 Pythonic。
"""

# ============================================================
# 1. 列表推导式 —— 代替 map()
# ============================================================
nums = [1, 2, 3, 4, 5]

# 传统写法
squares = []
for n in nums:
    squares.append(n ** 2)
print(squares)

# 推导式写法（一行搞定，对应 nums.map(n => n**2)）
squares = [n ** 2 for n in nums]
print(squares)

# 👉 试一试：用推导式生成 nums 里每个数的 3 倍


# ============================================================
# 2. 带条件 —— 代替 filter()
# ============================================================
# 只保留偶数（对应 nums.filter(n => n % 2 === 0)）
evens = [n for n in nums if n % 2 == 0]
print("偶数:", evens)

# map + filter 一起（先过滤偶数，再平方）
result = [n ** 2 for n in nums if n % 2 == 0]
print("偶数的平方:", result)

# 👉 试一试：从 nums 里取出大于 2 的数，并各加 100


# ============================================================
# 3. 三元 + 推导式 —— map 里带条件转换
# ============================================================
# 偶数标"双"，奇数标"单"（对应 nums.map(n => n%2 ? '单' : '双')）
labels = ["双" if n % 2 == 0 else "单" for n in nums]
print(labels)

# 👉 试一试：把 nums 里小于 3 的变成 0，其余保持不变


# ============================================================
# 4. 处理字符串列表 —— 实战常见
# ============================================================
words = ["  Hello ", "WORLD", " Python "]

# 去空格 + 转小写
cleaned = [w.strip().lower() for w in words]
print(cleaned)               # ['hello', 'world', 'python']

# 只保留长度大于 5 的单词
names = ["Tom", "Jennifer", "Bob", "Alexander"]
long_names = [n for n in names if len(n) > 5]
print(long_names)            # ['Jennifer', 'Alexander']

# 👉 试一试：把 words 里每个单词去空格后取首字母大写（提示：.strip().capitalize()）


# ============================================================
# 5. 字典推导式 —— 生成字典
# ============================================================
# 生成 {数字: 平方} 的字典
square_map = {n: n ** 2 for n in range(1, 6)}
print(square_map)            # {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}

# 把两个列表合成字典（对应实战中常见的数据组装）
keys = ["name", "age", "city"]
values = ["小明", 28, "北京"]
person = {k: v for k, v in zip(keys, values)}   # zip 把两列表配对
print(person)

# 👉 试一试：生成一个字典，键是 1-5，值是「键是否为偶数」(True/False)


# ============================================================
# 6. 集合推导式
# ============================================================
# 取一句话里所有不重复的单词长度
sentence = "the quick brown fox jumps"
length_set = {len(word) for word in sentence.split()}
print(length_set)


print("\n[完成] Day 6 跑通了！去 ROADMAP.md 勾掉 Day 6。")
