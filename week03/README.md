# 第 3 周 · 工程化 + 第一个真项目

P1 阶段收尾周。前两周学的是「语言」，这一周学的是「拿语言干活」：读写文件、调外部 API、用 pydantic 把脏数据收拾干净，最后用这些拼出一个能跑的 **Hacker News 阅读器 CLI**，再用 pytest 给它写测试。

> 通关标准：不查语法写出 100+ 行、带函数和类、能调 API 的脚本。

## 运行方式

```powershell
.\.venv\Scripts\Activate.ps1
python week03\day15_file_io_json.py
```

本周用到的第三方库（已装好，day16/17 会讲它们怎么来的）：

```powershell
pip install requests pydantic pytest
```

## 本周文件

| 文件 | 主题 | 对应你已会的前端知识 |
|---|---|---|
| `day15_file_io_json.py` | 文件读写 + JSON 序列化 | `fs.readFile` / `JSON.parse` `JSON.stringify` |
| `day16_requests_api.py` | `requests` 调 HTTP API | `fetch` / `axios` |
| `day17_pydantic.py` | pydantic 数据校验与建模 | `zod` / TS interface + 运行时校验 |
| `day18_hn_models.py` | 🛠️ 项目①：建模 + 拉数据 | 定义接口类型 + 调接口 |
| `day19_hn_cache_format.py` | 🛠️ 项目②：本地 JSON 缓存 + 格式化输出 | localStorage 缓存 + 渲染 |
| `day20_hn_cli.py` | 🛠️ 项目③：并发拉取 + argparse 命令行 | `Promise.all` + 命令行参数 |
| `test_day20.py` | day21：给项目写 pytest 测试 | jest / vitest |
| `day21_review.py` | pytest 用法讲解 + 本周小结 | — |

## 项目：Hacker News 阅读器

用 HN 官方 API（无需 key）做一个命令行阅读器：

```powershell
# 看前 10 条热门
python week03\day20_hn_cli.py --top 10

# 只看分数 > 300 的，并保存到本地
python week03\day20_hn_cli.py --top 30 --min-score 300 --save
```

数据流：`拉 topstories ID 列表` → `并发拉每条详情` → `pydantic 校验建模` → `按分数过滤/排序` → `格式化打印` → `缓存到 hn_cache.json`。

HN API 速查：
- 热门列表：`GET https://hacker-news.firebaseio.com/v0/topstories.json` → 返回一个 ID 数组
- 单条详情：`GET https://hacker-news.firebaseio.com/v0/item/{id}.json` → 返回 `{id, title, by, score, url, time, descendants, ...}`

## JS → Python 工程化对照

| JavaScript | Python | 备注 |
|---|---|---|
| `fs.readFileSync(p,'utf8')` | `open(p, encoding='utf8').read()` | 推荐用 `with open(...)` |
| `JSON.parse(s)` | `json.loads(s)` | s→对象 |
| `JSON.stringify(o, null, 2)` | `json.dumps(o, indent=2, ensure_ascii=False)` | 中文要加 `ensure_ascii=False` |
| `await fetch(url)` | `requests.get(url)` | requests 是同步的 |
| `res.json()` | `res.json()` | 一样 |
| `res.ok` / `res.status` | `res.ok` / `res.status_code` | |
| `zod.object({...})` | `class M(BaseModel): ...` | pydantic |
| `schema.parse(data)` | `M(**data)` / `M.model_validate(data)` | 校验失败抛异常 |
| `Promise.all(ids.map(fetchOne))` | `ThreadPoolExecutor.map(fetch_one, ids)` | 见 day20 |
| `process.argv` / yargs | `argparse` | 标准库自带 |
</content>
