"""
第 1 周 Day 2 — 列表 list 与元组 tuple（对照 JS 数组）

运行：python week01\\day02_list_tuple.py
跟着 "# 👉 试一试" 改代码再运行。
"""

# ============================================================
# 1. 列表 list —— 就是 JS 的数组，但方法名不同
# ============================================================
fruits = ["apple", "banana", "cherry"]
print(fruits)
print(len(fruits))          # 3，对应 arr.length
print(fruits[0])            # apple，索引从 0 开始
print(fruits[-1])           # cherry，负索引取倒数第一个（JS 没有！）

# 增删改
fruits.append("orange")     # 末尾追加，对应 arr.push()
fruits.insert(1, "mango")   # 在索引 1 处插入
fruits.remove("banana")     # 删除指定值
popped = fruits.pop()       # 弹出末尾，对应 arr.pop()
print(fruits, "弹出了:", popped)

# 👉 试一试：用 append 再加两个水果，然后 print(len(fruits))
fruits.append("lemom")
fruits.append("peach")
print(fruits)


# ============================================================
# 2. 切片 slice —— 比 JS 强大得多
# ============================================================
nums = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
print(nums[2:5])     # [2, 3, 4]  从索引 2 到 5（不含 5）
print(nums[:3])      # [0, 1, 2]  开头到 3
print(nums[7:])      # [7, 8, 9]  从 7 到结尾
print(nums[::2])     # [0, 2, 4, 6, 8]  每隔 2 个取一个
print(nums[::-1])    # 反转列表！对应 [...arr].reverse()

# 👉 试一试：用切片取出 nums 的最后三个元素
print(nums[-3:])

# ============================================================
# 3. 常用操作
# ============================================================
scores = [88, 72, 95, 60, 100]
print("最大:", max(scores))      # 100
print("最小:", min(scores))      # 60
print("求和:", sum(scores))      # 415
print("排序:", sorted(scores))   # 升序，返回新列表（不改原列表）
print("降序:", sorted(scores, reverse=True))
print("包含 95?", 95 in scores)  # True，对应 arr.includes()

# 遍历（对应 for...of）
for s in scores:
    print("分数:", s)

# 带索引遍历（对应 arr.entries()）
for i, s in enumerate(scores):
    print(f"第 {i} 个分数是 {s}")

# 👉 试一试：用 for 循环算出 scores 里大于 80 的有几个
count = 0
for s in scores:
    if(s > 80):
        count += 1
print(f"大于 80 的分数有 {count} 个")

# ============================================================
# 4. 元组 tuple —— 不可变的列表（JS 没有对应物）
# ============================================================
point = (3, 4)              # 用圆括号，创建后不能改
x, y = point               # 解构赋值，对应 const [x, y] = point
print(f"x={x}, y={y}")

# point[0] = 99            # 这行会报错！元组不可修改
# 用途：表示"一组固定不变的数据"，比如坐标、RGB 颜色、数据库一行记录

# 👉 试一试：创建一个 RGB 颜色元组 (255, 0, 0) 并解构成 r, g, b 打印
rgb = (255, 0, 0)
r, g, b = rgb
print(f"红色值: {r}, 绿色值: {g}, 蓝色值: {b}")

print("\n[完成] Day 2 跑通了！去 ROADMAP.md 勾掉 Day 2。")
