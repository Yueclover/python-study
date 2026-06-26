"""
第 2 周 Day 9 — 装饰器 decorator（JS 没有的语法糖）

运行：python week02\\day09_decorator.py

核心：装饰器 = 一个"接收函数、返回新函数"的函数。
你懂 JS 的高阶函数（函数包函数）就懂它，@ 只是语法糖。
"""

# ============================================================
# 1. 先理解：函数是「一等公民」（和 JS 一样）
# ============================================================
def shout(text):
    return text.upper()

say = shout                 # 函数可以赋值给变量
print(say("hello"))         # HELLO

def apply(func, value):     # 函数可以当参数传（高阶函数）
    return func(value)

print(apply(shout, "hi"))   # HI


# ============================================================
# 2. 手写一个装饰器 —— 它就是个返回函数的函数
# ============================================================
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("调用前...")
        result = func(*args, **kwargs)      # 执行原函数
        print("调用后...")
        return result
    return wrapper


def hello():
    print("你好")

# 不用 @ 的写法（看清本质）：
hello = my_decorator(hello)
hello()
# 输出：调用前... / 你好 / 调用后...


# ============================================================
# 3. @ 语法糖 —— 和上面完全等价，但更优雅
# ============================================================
@my_decorator               # 等价于 greet = my_decorator(greet)
def greet():
    print("Hi there")

greet()

# 👉 试一试：写一个新函数 bye()，加上 @my_decorator 装饰它


# ============================================================
# 4. 实用例子 1：计时装饰器（统计函数耗时）
# ============================================================
import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        cost = time.time() - start
        print(f"{func.__name__} 耗时 {cost:.4f} 秒")
        return result
    return wrapper


@timer
def slow_task():
    total = sum(range(1_000_000))
    return total

slow_task()

# 👉 试一试：把 @timer 加到一个你自己写的函数上

@timer
def test():
    return 10

test()



# ============================================================
# 5. 实用例子 2：带参数的装饰器（装饰器工厂，多套一层）
# ============================================================
def repeat(times):                  # 最外层接收参数
    def decorator(func):            # 中间层接收函数
        def wrapper(*args, **kwargs):
            for _ in range(times):
                func(*args, **kwargs)
        return wrapper
    return decorator


@repeat(times=3)                    # 重复执行 3 次
def ping():
    print("ping")

ping()

# 👉 试一试：用 @repeat(times=5) 装饰一个打印你名字的函数


# ============================================================
# 为什么重要：FastAPI 的 @app.get("/")、@app.post() 全是装饰器。
# 第 4 周写后端时你会天天用到，现在理解原理，到时不慌。
# ============================================================

print("\n[完成] Day 9 跑通了！去 ROADMAP.md 勾掉 Day 9。")
