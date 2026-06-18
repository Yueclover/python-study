r"""
Day 15 · 文件 IO 读写 + JSON 处理
====================================
前端里你用 fs（Node）或 localStorage（浏览器）读写数据，
JSON.parse / JSON.stringify 转格式。Python 里对应 open() + json 模块。

跑它：  python week03\day15_file_io_json.py
"""

import sys
import json
from pathlib import Path

# Windows 控制台默认 GBK 编码，打印 emoji/特殊符号会崩。这行强制用 UTF-8 输出。
# （Mac/Linux 默认就是 UTF-8，这行写了也无害。）
sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# 1. 读写文本文件：with open(...)
# ---------------------------------------------------------------------------
# JS:  fs.writeFileSync('a.txt', 'hello', 'utf8')
# 关键：用 with，文件用完自动关闭（对应 day10 学的上下文管理器）。
# 不写 with 的话要手动 f.close()，忘了就泄漏文件句柄。

demo_dir = Path(__file__).parent / "_day15_tmp"   # 把临时文件都放一个文件夹
demo_dir.mkdir(exist_ok=True)                       # 类似 mkdir -p，存在不报错
txt_path = demo_dir / "note.txt"

with open(txt_path, "w", encoding="utf-8") as f:    # "w"=写（覆盖），encoding 一定要写
    f.write("第一行\n")
    f.write("第二行\n")

# 读整个文件
with open(txt_path, "r", encoding="utf-8") as f:    # "r"=读（默认）
    content = f.read()
print("整个文件内容：")
print(content)

# 按行读（大文件首选，不会一次性塞进内存）
with open(txt_path, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, start=1):
        print(f"  第{i}行: {line.rstrip()}")   # rstrip 去掉行尾的 \n

# 追加："a" = append，不覆盖
with open(txt_path, "a", encoding="utf-8") as f:
    f.write("追加的一行\n")

# ---------------------------------------------------------------------------
# 2. 文件模式速查（第一个参数）
# ---------------------------------------------------------------------------
# "r"  读（默认，文件不存在报错）
# "w"  写（覆盖，文件不存在则新建）
# "a"  追加
# "x"  新建（文件已存在则报错，防误覆盖）
# 加 "b" 是二进制，如 "rb" 读图片/字节

# ---------------------------------------------------------------------------
# 3. JSON：和前端思路完全一致
# ---------------------------------------------------------------------------
# JS:  JSON.stringify(obj)  /  JSON.parse(str)
# Py:  json.dumps(obj)      /  json.loads(str)
#       dumpS / loadS 的 s = string（字符串）
#       json.dump / json.load（不带 s）= 直接读写文件对象

data = {
    "name": "clover",
    "skills": ["js", "python"],
    "level": 3,
    "active": True,        # 注意：Python 的 True → JSON 的 true（自动转）
    "note": "中文测试",
}

# 对象 → JSON 字符串
s = json.dumps(data, ensure_ascii=False, indent=2)
#                    ^^^^^^^^^^^^^^^^^  不加这个，中文会变成 中文 转义
#                                       ^^^^^^^  indent=2 美化，对应 JSON.stringify(o,null,2)
print("\nJSON 字符串：")
print(s)

# JSON 字符串 → 对象
obj = json.loads(s)
print("\n解析回对象，取字段：", obj["name"], obj["skills"])

# ---------------------------------------------------------------------------
# 4. 直接读写 JSON 文件（最常用）
# ---------------------------------------------------------------------------
json_path = demo_dir / "data.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)   # 注意是 dump 不是 dumps

with open(json_path, "r", encoding="utf-8") as f:
    loaded = json.load(f)                                # 注意是 load 不是 loads
print("\n从文件读回的 JSON：", loaded["note"])

# ---------------------------------------------------------------------------
# 5. pathlib：比字符串拼路径更安全（跨平台，Win 的 \ 和 Mac 的 / 自动处理）
# ---------------------------------------------------------------------------
# JS 里你用 path.join(__dirname, 'a', 'b')，Python 用 / 运算符拼 Path。
p = Path(__file__)
print("\n--- pathlib 演示 ---")
print("当前文件名：", p.name)          # day15_file_io_json.py
print("所在目录：", p.parent.name)     # week03
print("后缀：", p.suffix)              # .py
print("是否存在：", json_path.exists())
print("文件大小(字节)：", json_path.stat().st_size)

# pathlib 还能一行读写（小文件偷懒用）
quick = demo_dir / "quick.txt"
quick.write_text("一行搞定写入\n", encoding="utf-8")
print("一行读出：", quick.read_text(encoding="utf-8").strip())

# ---------------------------------------------------------------------------
# 练习（改完再跑）
# ---------------------------------------------------------------------------
# 1) 写一个函数 save_json(path, obj) 和 load_json(path)，把上面的样板封装起来——
#    day18 项目缓存就会用到。
# 2) 读 data.json，把 level 改成 4，再写回去（读→改→写 三步）。
# 3) 用 "x" 模式创建一个文件，再跑一次，观察 FileExistsError，用 try/except 接住它。

if __name__ == "__main__":
    print("\n✅ day15 跑通。临时文件在：", demo_dir)
