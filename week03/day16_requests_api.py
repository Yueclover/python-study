r"""
Day 16 · 用 requests 调外部 API
====================================
前端：fetch / axios。Python 最常用的是 requests 库（第三方，不在标准库）。
注意：requests 是「同步」的——调一次就卡住等返回，不像 fetch 返回 Promise。
（异步版要用 httpx / aiohttp，day20 会用并发绕过这个限制。）

先装（已经装好了，知道命令就行）：
    pip install requests

跑它：  python week03\day16_requests_api.py
"""

import sys
import requests

sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK，强制 UTF-8 才能打印特殊符号

# ---------------------------------------------------------------------------
# 1. 最基础的 GET
# ---------------------------------------------------------------------------
# JS:  const res = await fetch(url); const data = await res.json();
# Py:  res = requests.get(url);      data = res.json()
#      —— 没有 await，因为 requests 是同步的，这一行会一直等到服务器返回。

HN = "https://hacker-news.firebaseio.com/v0"   # 本周项目就用这个 API

res = requests.get(f"{HN}/topstories.json", timeout=10)
#                                            ^^^^^^^^^^ 永远写 timeout！
#                                            不写的话网络卡了会无限等待。

print("状态码：", res.status_code)   # 200 表示成功，对应 fetch 的 res.status
print("res.ok：", res.ok)            # True/False，2xx 即 True（和 fetch 一样）

ids = res.json()                      # 把响应体按 JSON 解析成 Python 对象（这里是 list）
print("热门故事数量：", len(ids))
print("前 5 个 ID：", ids[:5])

# ---------------------------------------------------------------------------
# 2. 拉单条详情 + 检查错误
# ---------------------------------------------------------------------------
first_id = ids[0]
res = requests.get(f"{HN}/item/{first_id}.json", timeout=10)

# raise_for_status()：4xx/5xx 时抛异常。比手动 if res.ok 更省事，
# 配合 day10 学的 try/except 用。JS 里 fetch 不会因 404 reject，这点 Python 更省心。
res.raise_for_status()

item = res.json()
print("\n第一条热门：")
print("  标题：", item.get("title"))     # 用 .get() 取，字段缺失返回 None 而不报错
print("  作者：", item.get("by"))
print("  分数：", item.get("score"))
print("  链接：", item.get("url"))
print("  评论数：", item.get("descendants"))

# ---------------------------------------------------------------------------
# 3. 查询参数、请求头（虽然 HN 用不上，但你迟早要用）
# ---------------------------------------------------------------------------
# JS:  fetch(url + '?q=python&page=2', { headers: {...} })
# Py:  requests 帮你拼 query string，传 dict 即可：
demo = requests.get(
    "https://httpbin.org/get",                 # 一个回显你请求的测试服务
    params={"q": "python", "page": 2},         # → ?q=python&page=2
    headers={"User-Agent": "py-study/1.0"},
    timeout=10,
)
echo = demo.json()
print("\nhttpbin 回显的查询参数：", echo["args"])

# POST 的写法（项目用不到，留个印象）：
# requests.post(url, json={"key": "value"}, timeout=10)
#   json=... 会自动设 Content-Type: application/json 并序列化（对应 axios.post 的第二参数）

# ---------------------------------------------------------------------------
# 4. 处理网络错误：一定要包 try/except
# ---------------------------------------------------------------------------
def fetch_item(item_id: int) -> dict | None:
    """拉一条 HN item，失败返回 None（项目里会复用这个思路）。"""
    try:
        r = requests.get(f"{HN}/item/{item_id}.json", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        # RequestException 是所有 requests 异常的基类：超时/连接失败/HTTP错误 都抓得到
        print(f"  拉取 {item_id} 失败：{e}")
        return None

print("\n用封装函数拉第二条：", fetch_item(ids[1])["title"])

# ---------------------------------------------------------------------------
# 5. Session：复用连接（拉很多条时更快）
# ---------------------------------------------------------------------------
# 项目要拉几十条，每次新建连接慢。Session 会复用 TCP 连接（类似 axios 实例）。
with requests.Session() as session:
    session.headers.update({"User-Agent": "py-study/1.0"})
    titles = []
    for sid in ids[2:5]:
        r = session.get(f"{HN}/item/{sid}.json", timeout=10)
        titles.append(r.json().get("title"))
    print("\n用 Session 连拉 3 条标题：")
    for t in titles:
        print("  -", t)

# ---------------------------------------------------------------------------
# 练习
# ---------------------------------------------------------------------------
# 1) 把 fetch_item 改造成支持 base_url 参数，方便测试时换地址。
# 2) 故意把 timeout 改成 0.001，观察会抛什么异常，用 except 接住。
# 3) 拉前 10 条 ID 的标题，按分数从高到低排序打印——day18 会正式做这件事。

if __name__ == "__main__":
    print("\n✅ day16 跑通。下一步：day17 用 pydantic 把这堆 dict 变成有类型的对象。")
