"""
第 1 周 Day 3 — 字典 dict 与集合 set（对照 JS 对象/Map/Set）

运行：python week01\\day03_dict_set.py
"""

# ============================================================
# 1. 字典 dict —— 对应 JS 对象，但键要加引号
# ============================================================
user = {
    "name": "小明",
    "age": 28,
    "skills": ["JS", "Python"],
}
print(user["name"])              # 小明，取值
print(user.get("email"))         # None，键不存在不报错（推荐用法）
print(user.get("email", "无"))   # 无，提供默认值

# 增改删
user["email"] = "ming@x.com"     # 新增/修改键
user["age"] = 29
del user["age"]                  # 删除键
print(user)

# 判断键是否存在（对应 'name' in obj）
print("name" in user)            # True

# 👉 试一试：给 user 加一个 "city" 键并打印整个字典
user["city"] = "Nanjing"
print(user)


# ============================================================
# 2. 遍历字典
# ============================================================
prices = {"apple": 5, "banana": 3, "cherry": 20}

for key in prices:                       # 默认遍历键
    print("水果:", key)

for key, value in prices.items():        # 同时拿键和值（最常用）
    print(f"{key} 卖 {value} 元")

print("所有键:", list(prices.keys()))    # 对应 Object.keys()
print("所有值:", list(prices.values()))  # 对应 Object.values()

# 👉 试一试：用 for 循环算出 prices 里所有水果的总价（sum 思路）
total_price = 0
for price in prices.values():
    total_price += price
print(f"所有水果的总价是 {total_price} 元")
    

# ============================================================
# 3. 嵌套结构 —— 这就是 JSON，AI 接口返回的都长这样
# ============================================================
response = {
    "status": "ok",
    "data": {
        "users": [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
        ]
    },
}
# 一层层取值（对应 response.data.users[0].name）
print(response["data"]["users"][0]["name"])   # A

# 👉 试一试：打印第二个用户的 id
print(response["data"]["users"][1]["id"])

# ============================================================
# 4. 集合 set —— 自动去重，对应 JS 的 Set
# ============================================================
tags = {"python", "ai", "python", "web"}   # 重复的 python 自动合并
print(tags)                                 # 只剩 3 个

a = {1, 2, 3, 4}
b = {3, 4, 5, 6}
print("交集:", a & b)    # {3, 4}
print("并集:", a | b)    # {1, 2, 3, 4, 5, 6}
print("差集:", a - b)    # {1, 2}

# 给列表去重的常用技巧
nums = [1, 1, 2, 3, 3, 3]
print("去重:", list(set(nums)))   # [1, 2, 3]

# 👉 试一试：用 set 找出两个列表 [1,2,3] 和 [2,3,4] 的共同元素
l1 = [1, 2, 3]
l2 = [2, 3, 4]
print("共同元素:", list(set(l1) & set(l2)))


print("\n[完成] Day 3 跑通了！去 ROADMAP.md 勾掉 Day 3。")
