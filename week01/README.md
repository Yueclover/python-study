# 第 1 周 · Python 语法对照速成

你已经会编程，这一周只是把 JS 概念翻译成 Python。每天跑一个文件，边读边改。

## 怎么开始

1. 激活虚拟环境（在项目根目录 `python-study` 下执行）：

   **PowerShell：**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   看到命令行前面出现 `(.venv)` 就成功了。

   > 如果报错 "无法加载...禁止运行脚本"，先执行一次：
   > ```powershell
   > Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   > ```

2. 运行当天的文件：
   ```powershell
   python week01\day01_basics.py
   ```

3. 打开文件，跟着注释里的 `# 👉 试一试` 改代码、再运行，观察变化。

## 本周文件
- `day01_basics.py` — 变量、类型、字符串、输入输出（今天先跑这个）
- 后续 day02~day07 你可以照着 `ROADMAP.md` 自己建，或让我帮你生成。

## JS → Python 速查表

| JavaScript | Python | 备注 |
|---|---|---|
| `let x = 1` | `x = 1` | 无需声明关键字 |
| `const PI = 3.14` | `PI = 3.14` | 约定大写表示常量，无强制 |
| `console.log(x)` | `print(x)` | |
| `// 注释` | `# 注释` | |
| `\`Hi ${name}\`` | `f"Hi {name}"` | f-string |
| `[1,2,3]` | `[1, 2, 3]` | list |
| `{a: 1}` | `{"a": 1}` | dict，键要引号 |
| `=== / !==` | `== / !=` | Python 无类型转换坑 |
| `&&  ||  !` | `and  or  not` | |
| `null / undefined` | `None` | |
| `true / false` | `True / False` | 首字母大写 |
| `arr.length` | `len(arr)` | |
| `arr.map(f)` | `[f(x) for x in arr]` | 推导式 |
| `function f(){}` | `def f():` | |
| `arr.push(x)` | `arr.append(x)` | |

> 最大区别：Python 用**缩进**表示代码块，没有 `{}`。统一用 4 个空格。
