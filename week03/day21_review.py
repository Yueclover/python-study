r"""
Day 21 · pytest 用法讲解 + 第 3 周小结
========================================
真正的测试代码在 test_day20.py（pytest 约定测试写在 test_*.py 里）。
这个文件是「讲解 + 小结」，读它，然后去跑 test_day20.py。

跑测试（在项目根目录，先激活 venv）：
    pytest week03\test_day20.py -v        # -v 显示每个测试名
    pytest week03 -v                       # 跑 week03 下所有测试
    pytest week03\test_day20.py -k score   # 只跑名字含 score 的测试
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，强制 UTF-8 才能打印 emoji/特殊符号

# ---------------------------------------------------------------------------
# 1. pytest 的三条核心约定（对应你熟的 jest/vitest）
# ---------------------------------------------------------------------------
# - 文件名：test_*.py 或 *_test.py        （jest: *.test.js）
# - 函数名：test_*                          （jest: test(...) / it(...)）
# - 断言：直接用 Python 的 assert           （jest: expect(x).toBe(y)）
#         pytest 会把 assert 失败的两边值漂亮地打印出来，不需要 expect 链式 API。

# 一个最小例子：
def add(a, b):
    return a + b

def test_add():            # pytest 会自动发现并运行这个函数
    assert add(2, 3) == 5  # 失败时 pytest 会显示 "assert 5 == 6" 这种对比


# ---------------------------------------------------------------------------
# 2. 你在 test_day20.py 里用到的 pytest 利器
# ---------------------------------------------------------------------------
# @pytest.mark.parametrize  —— 一份测试逻辑跑多组数据（= jest 的 test.each）
# @pytest.fixture           —— 可复用的测试数据/环境，函数声明它做参数就能拿到
#                              （= jest 的 beforeEach + 共享 setup）
# pytest.raises(SomeError)  —— 断言「这段代码应该抛某异常」
#                              with pytest.raises(ValueError):
#                                  int("abc")

# ---------------------------------------------------------------------------
# 3. 为什么我们只测「纯函数」，拉网络的怎么办？
# ---------------------------------------------------------------------------
# 纯函数（time_ago / filter_stories）：输入定→输出定，测起来稳、快。优先测它们。
#
# 拉网络的函数（fetch_story）：真去请求会慢、会因网络/数据变化而时好时坏（flaky）。
# 解决办法是 mock —— 把 requests.get 换成一个假的、返回写死数据的函数：
#
#     from unittest.mock import patch
#     def test_fetch_story_parses(monkeypatch):
#         fake = {"id": 1, "title": "x", "by": "a", "score": 9}
#         class FakeResp:
#             def raise_for_status(self): pass
#             def json(self): return fake
#         monkeypatch.setattr("day18_hn_models.requests.Session.get",
#                             lambda self, url, **kw: FakeResp())
#         ...
#
# monkeypatch 是 pytest 自带的 fixture（不用装），临时替换掉真实依赖。
# 这就是「单元测试」的精髓：把被测逻辑和外部世界（网络/时间/随机）隔离开。

# ---------------------------------------------------------------------------
# 4. 关于 TDD（superpowers 里的核心流程，下阶段会大量用）
# ---------------------------------------------------------------------------
# 顺序反过来：先写测试（红）→ 写最少代码让它过（绿）→ 重构（保持绿）。
# 第 4 周起做 FastAPI，强烈建议正式用 TDD。现在先建立「写完功能顺手补测试」的肌肉记忆。


def 本周小结():
    print("""
┌─────────────────────────────────────────────────────────┐
│  第 3 周完成 ✅  P1「Python 速成」阶段收尾                  │
├─────────────────────────────────────────────────────────┤
│  day15  文件 IO + JSON       open() / json / pathlib       │
│  day16  requests 调 API      get / timeout / Session       │
│  day17  pydantic 建模校验    BaseModel / Field / validator │
│  day18  项目①  建模+拉数据    模型 + 数据获取层分离          │
│  day19  项目②  缓存+格式化    JSON 缓存 + 纯函数渲染         │
│  day20  项目③  并发+CLI       ThreadPool + argparse         │
│  day21  pytest 测试          assert / parametrize / fixture │
└─────────────────────────────────────────────────────────┘

通关检查（对照 ROADMAP P1 通关标准）：
  [ ] 不查语法能独立写出 100+ 行、带函数和类、能调 API 的脚本
      → day20_hn_cli.py 就是，试着不看它从零默写一遍
  [ ] 理解了文件读写、HTTP 请求、数据校验三件套
  [ ] 跑通 pytest，绿了

下一阶段预告（第 4-6 周 · P2 后端工程）：
  第 4 周 FastAPI —— 你这周写的 HN 阅读器逻辑，下周会包成一个 Web API。
  pydantic 在 FastAPI 里是一等公民，这周没白学。

记得去 ROADMAP.md 把第 2、3 周的 [ ] 勾成 [x]！
""")


if __name__ == "__main__":
    test_add()
    本周小结()
    print("✅ 读完了？现在去跑：pytest week03\\test_day20.py -v")
