"""
第 2 周 Day 14 — 综合复盘项目：迷你异步任务系统

运行：python week02\\day14_review.py

把本周所有知识串起来：
  类 + 继承 + @property（Day8）
  装饰器（Day9）
  异常处理（Day10）
  类型注解（Day12）
  async/await + gather（Day13）

建议先读懂，再做文末的「毕业挑战」。
"""
import asyncio
import time
from typing import Optional


# ============================================================
# 1. 装饰器：记录每个任务的执行耗时
# ============================================================
def log_time(func):
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        print(f"  [{func.__name__}] 完成，耗时 {time.time() - start:.2f}s")
        return result
    return wrapper


# ============================================================
# 2. 类 + 继承：任务基类与具体任务
# ============================================================
class Task:
    def __init__(self, name: str, duration: float) -> None:
        self.name = name
        self.duration = duration
        self.done = False

    @property
    def status(self) -> str:                # @property：当属性访问
        return "已完成" if self.done else "未完成"

    async def run(self) -> str:
        await asyncio.sleep(self.duration)
        self.done = True
        return f"{self.name} 的结果"


class DownloadTask(Task):                    # 继承
    def __init__(self, name: str, duration: float, url: str) -> None:
        super().__init__(name, duration)
        self.url = url

    async def run(self) -> str:             # 重写
        if not self.url.startswith("http"):
            raise ValueError(f"非法 URL: {self.url}")   # 异常处理演示
        await asyncio.sleep(self.duration)
        self.done = True
        return f"已下载 {self.url}"


# ============================================================
# 3. 任务管理器：并发执行所有任务（asyncio.gather）
# ============================================================
class TaskManager:
    def __init__(self) -> None:
        self.tasks: list[Task] = []

    def add(self, task: Task) -> None:
        self.tasks.append(task)

    @log_time
    async def run_one(self, task: Task) -> Optional[str]:
        try:
            return await task.run()
        except ValueError as e:
            print(f"  任务出错: {e}")
            return None

    async def run_all(self) -> list:
        print("开始并发执行所有任务...")
        results = await asyncio.gather(*[self.run_one(t) for t in self.tasks])
        return results


# ============================================================
# 4. 跑起来
# ============================================================
async def main():
    manager = TaskManager()
    manager.add(Task("数据清洗", 1.0))
    manager.add(DownloadTask("下载模型", 1.5, "https://example.com/model"))
    manager.add(DownloadTask("坏任务", 0.5, "ftp://bad"))   # 故意触发异常

    start = time.time()
    results = await manager.run_all()
    print(f"\n全部完成，总耗时 {time.time() - start:.2f}s（并发，约等于最慢任务）")

    print("\n=== 结果汇总 ===")
    for task, result in zip(manager.tasks, results):
        print(f"{task.name}: {task.status} | 结果: {result}")


asyncio.run(main())


# ============================================================
# 毕业挑战（自己动手）：
#   1. 新增一个 ComputeTask(Task)，run() 里计算 sum(range(N)) 并返回。
#   2. 给 TaskManager 加一个 @property，返回已完成任务的数量。
#   3. 给 log_time 装饰器加上：耗时超过 1 秒就额外打印 "（慢任务警告）"。
# 做完这三个，你就真正把第 2 周的知识融会贯通了。
# ============================================================

print("\n[完成] 第 2 周全部跑通！你已掌握类/装饰器/异常/类型注解/异步。")
print("下一步：勾掉 Day 14，准备进入第 3 周（文件IO/requests/pydantic + 第一个CLI项目）。")
