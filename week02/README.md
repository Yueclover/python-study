# 第 2 周 · Python 进阶特性（JS 里没有或差别很大）

这一周是分水岭。前端有对应概念的会标注，没对应的（装饰器、上下文管理器、`__dunder__`）要重点理解。

## 运行方式
```powershell
.\.venv\Scripts\Activate.ps1
python week02\day08_class.py
```

## 本周文件
- `day08_class.py` — 类与对象、`__init__`、`self`、继承（对应 JS class，但更强）
- `day09_decorator.py` — 装饰器（JS 没有，但你懂高阶函数就好理解）
- `day10_context_exception.py` — `with` 上下文管理器 + 异常处理
- `day11_env_packages.py` — 虚拟环境、pip、pyproject.toml（说明文档+命令）
- `day12_type_hints.py` — 类型注解（会 TS 就秒懂，AI 库全靠它）
- `day13_async.py` — async/await（和 JS 几乎一样，直接迁移）
- `day14_review.py` — 综合项目：用类+装饰器+异步搭一个迷你任务系统

## JS → Python 进阶对照

| JavaScript | Python | 备注 |
|---|---|---|
| `class A {}` | `class A:` | |
| `constructor()` | `def __init__(self):` | self 要手写 |
| `this` | `self` | 且每个方法第一个参数都要写 self |
| `extends` | `class B(A):` | 括号里写父类 |
| `super()` | `super().__init__()` | |
| 高阶函数包装 | `@decorator` | 语法糖，JS 无 |
| `try/catch/finally` | `try/except/finally` | catch→except |
| `throw new Error()` | `raise ValueError()` | |
| `async function` | `async def` | |
| `await fetch()` | `await ...` | 几乎一样 |
| `Promise.all([])` | `asyncio.gather()` | |
| TS `x: string` | `x: str` | 运行时不强制，靠工具检查 |
