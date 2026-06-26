"""
第 2 周 Day 11 — 虚拟环境、包管理、项目结构

运行：python week02\\day11_env_packages.py

今天偏"概念+命令"，类比前端的 node_modules / package.json 来理解。
下面代码演示如何查看当前环境信息，命令部分请在终端实操。
"""
import sys

# ============================================================
# 1. 查看当前 Python 环境
# ============================================================  
print("Python 版本:", sys.version.split()[0])
print("解释器路径:", sys.executable)   # 如果在 .venv 里，路径会含 .venv
print("是否在虚拟环境:", hasattr(sys, "real_prefix") or sys.prefix != sys.base_prefix)


# ============================================================
# 2. 前端 vs Python 包管理对照（重点记这张表）
# ============================================================
mapping = {
    "node_modules/         ": ".venv/  (虚拟环境，隔离依赖)",
    "package.json          ": "pyproject.toml  (项目+依赖声明)",
    "package-lock.json     ": "uv.lock / requirements.txt  (锁定版本)",
    "npm install           ": "pip install xxx",
    "npm install -D xxx    ": "pip install xxx  (Python 不区分 dev 那么严格)",
    "npm run dev           ": "python main.py / uvicorn main:app",
    "npx                   ": "uvx / python -m xxx",
}
print("\n=== 前端 → Python 包管理对照 ===")
for k, v in mapping.items():
    print(f"  {k} → {v}")


# ============================================================
# 3. 你需要在【终端】实操的命令（不在本脚本里运行）
# ============================================================
GUIDE = """
=== 终端实操清单（在项目根目录执行）===

# 1) 创建虚拟环境（项目根目录已有 .venv，可跳过）
python -m venv .venv

# 2) 激活（每次开新终端都要激活）
.\\.venv\\Scripts\\Activate.ps1        # PowerShell
# 看到行首出现 (.venv) 即成功

# 3) 安装一个第三方库试试（HTTP 请求库，第 3 周要用）
pip install requests

# 4) 查看已装的包
pip list

# 5) 把当前依赖导出成清单（别人/服务器照此安装）
pip freeze > requirements.txt

# 6) 别人拿到项目后，一键还原所有依赖
pip install -r requirements.txt

# 7) 退出虚拟环境
deactivate

=== 进阶推荐：uv（更快的现代工具，相当于 pnpm 之于 npm）===
# 安装 uv 后：
#   uv venv          创建环境
#   uv pip install   装包（比 pip 快很多）
#   uv add requests  加依赖并写入 pyproject.toml
"""
print(GUIDE)


# ============================================================
# 4. 标准项目结构长什么样（心里有个数）
# ============================================================
STRUCTURE = """
my-ai-app/
├── .venv/                # 虚拟环境（不提交 git）
├── .gitignore           # 忽略 .venv/ __pycache__/ .env 等
├── pyproject.toml       # 项目元信息 + 依赖
├── requirements.txt     # 依赖清单（或用 uv.lock）
├── .env                 # 密钥等环境变量（绝不提交 git！）
├── README.md
└── src/
    └── app/
        ├── __init__.py  # 有这个文件，文件夹才是「包」
        └── main.py
"""
print("=== 典型项目结构 ===")
print(STRUCTURE)

# 👉 实操作业：
#   1. 激活 .venv，运行 pip install requests，再 pip list 看有没有 requests
#   2. 运行 pip freeze > requirements.txt，打开看看里面是什么
#   3. 在项目根目录建一个 .gitignore，写入一行 .venv/

print("[完成] Day 11 跑通了！去终端做完实操作业，再勾掉 Day 11。")
