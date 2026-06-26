"""
第 2 周 Day 13 — 异步 async/await（和 JS 几乎一样，直接迁移）

运行：python week02\\day13_async.py

你写过 JS 的 async/await 和 Promise，这一天会非常轻松。
最大区别：Python 要用 asyncio.run() 启动事件循环。
"""
import asyncio
import time


# ============================================================
# 1. 定义异步函数 —— async def，对应 async function
# ============================================================
async def say_hello():
    print("开始")
    await asyncio.sleep(1)          # 对应 await new Promise(r => setTimeout(r, 1000))
    print("1 秒后")
    return "完成"


# 关键区别：不能直接调用 say_hello()，要用 asyncio.run() 启动
result = asyncio.run(say_hello())
print("返回值:", result)


# ============================================================
# 2. 串行 vs 并发 —— 体会 await 的威力
# ============================================================
async def fetch(name, seconds):
    print(f"  {name} 开始")
    await asyncio.sleep(seconds)        # 模拟网络请求耗时
    print(f"  {name} 完成（耗时 {seconds}s）")
    return f"{name} 的数据"


async def run_serial():
    """串行：一个接一个，总耗时 = 各任务之和"""
    start = time.time()
    await fetch("任务A", 1)
    await fetch("任务B", 1)
    await fetch("任务C", 1)
    print(f"串行总耗时: {time.time() - start:.1f}s（约 3 秒）")


async def run_concurrent():
    """并发：同时跑，总耗时 = 最慢的那个。对应 Promise.all()"""
    start = time.time()
    results = await asyncio.gather(     # 对应 await Promise.all([...])
        fetch("任务A", 1),
        fetch("任务B", 1),
        fetch("任务C", 1),
    )
    print(f"并发总耗时: {time.time() - start:.1f}s（约 1 秒）")
    print("所有结果:", results)


print("\n--- 串行 ---")
asyncio.run(run_serial())

print("\n--- 并发（gather）---")
asyncio.run(run_concurrent())

# 👉 试一试：给 run_concurrent 再加一个 fetch("任务D", 2)，看总耗时变成几秒


# ============================================================
# 3. 实战意义：调多个 AI / API 时，并发能省大量时间
# ============================================================
async def call_llm(prompt, delay):
    """模拟调用一次大模型（真实场景就是 await client.messages.create(...)）"""
    await asyncio.sleep(delay)
    return f"对【{prompt}】的回答"


async def batch_ask():
    prompts = ["介绍 Python", "什么是 RAG", "解释装饰器"]
    # 三个问题并发问，而不是排队等
    answers = await asyncio.gather(*[call_llm(p, 0.5) for p in prompts])
    for q, a in zip(prompts, answers):
        print(f"Q: {q}\nA: {a}\n")


print("--- 并发调用多个 LLM（模拟）---")
asyncio.run(batch_ask())

# 👉 试一试：把 prompts 列表再加两个问题，观察依然是并发执行


# ============================================================
# 小结：async def / await / asyncio.gather 三件套，
# 第 6 周做流式 API、第 7 周调 LLM 时天天用。和 JS 思路完全一致。
# ============================================================

print("[完成] Day 13 跑通了！去 ROADMAP.md 勾掉 Day 13。")
