# Python → AI 应用开发工程师 · 16 周学习路线

> 背景：前端工程师 · 零 Python 基础 · 2-3h/天 · 目标 LLM 应用 + AI 后端
> 用法：每天完成后把 `[ ]` 改成 `[x]`。每周日做一次小结。

---

## 进度总览

- [ ] **P1 Python 速成**（第 1-3 周）
- [ ] **P2 后端工程**（第 4-6 周）
- [ ] **P3 LLM 应用核心**（第 7-12 周）⭐
- [ ] **P4 综合项目 + 上线**（第 13-16 周）

每日节奏：`90min 主线手敲` + `30min 练习/扩展` + `15min 笔记`

---

## P1 · Python 速成（第 1-3 周）

### 第 1 周 — 语法对照（你已会概念，只是换语法）
- [x] Day 1：环境 + 变量/类型/print/输入（对照 JS）→ `week01/day01_basics.py`
- [x] Day 2：列表 list & 元组 tuple（对照数组）→ `week01/day02_list_tuple.py`
- [x] Day 3：字典 dict & 集合 set（对照对象/Map/Set）→ `week01/day03_dict_set.py`
- [x] Day 4：条件 if/elif/else + 循环 for/while → `week01/day04_control_flow.py`
- [ ] Day 5：函数 def、参数、返回值、作用域 → `week01/day05_functions.py`
- [ ] Day 6：推导式 list/dict comprehension（JS 没有的利器）→ `week01/day06_comprehension.py`
- [ ] Day 7：小结综合项目 + LeetCode 复盘 → `week01/day07_review.py`

### 第 2 周 — Python 特性（JS 里没有，重点）
- [ ] Day 8：类与对象、`__init__`、`self`
- [ ] Day 9：装饰器 decorator
- [ ] Day 10：上下文管理器 `with`、异常 try/except
- [ ] Day 11：虚拟环境 venv、pip、`pyproject.toml`
- [ ] Day 12：类型注解 type hints（会 TS 秒懂）
- [ ] Day 13：异步 async/await（迁移 JS 知识）
- [ ] Day 14：小结 + 整合练习

### 第 3 周 — 工程化 + 第一个项目
- [ ] Day 15：文件 IO 读写、JSON 处理
- [ ] Day 16：`requests` 调外部 API
- [ ] Day 17：`pydantic` 数据校验入门
- [ ] Day 18-20：**项目** — CLI 工具（调公开 API 并格式化输出）
- [ ] Day 21：`pytest` 写测试 + 小结

> ✅ 通关：不查语法写出 100 行、带函数和类、能调 API 的脚本。

---

## P2 · 后端工程（第 4-6 周）

### 第 4 周 — FastAPI 入门
- [ ] 路由、路径/查询参数
- [ ] 请求/响应模型（Pydantic）
- [ ] 自动 Swagger 文档
- [ ] 依赖注入 Depends
- [ ] 异步路由
- [ ] **练习**：实现一个 TODO API

### 第 5 周 — 数据与持久化
- [ ] SQL 基础（SELECT/INSERT/UPDATE/JOIN）
- [ ] SQLite + SQLAlchemy ORM
- [ ] 数据库迁移（Alembic）
- [ ] `.env` 环境变量与配置分层
- [ ] async 数据库操作

### 第 6 周 — 生产化 + 项目
- [ ] 中间件、CORS、错误处理、日志
- [ ] JWT 认证
- [ ] 流式响应 StreamingResponse（LLM 必用）
- [ ] Docker 打包
- [ ] **项目**：带用户系统 + 数据库的 REST API

> ✅ 通关：独立设计实现有数据库、有认证、有文档的 API 服务。

---

## P3 · LLM 应用核心（第 7-12 周）⭐

### 第 7 周 — LLM API 基础
- [ ] Claude / OpenAI API：messages 结构、system prompt
- [ ] temperature、token、上下文窗口
- [ ] 流式输出 streaming
- [ ] Python SDK 封装对话服务
- [ ] token 计费与模型选型

### 第 8 周 — Prompt 工程 + 结构化输出
- [ ] system prompt 设计、few-shot、思维链 CoT
- [ ] JSON mode / 结构化输出
- [ ] Pydantic 解析模型返回

### 第 9 周 — 工具调用 Tool Calling
- [ ] tool/function calling 原理
- [ ] 让模型调用自定义函数（查库/调 API）
- [ ] 多工具编排

### 第 10 周 — RAG 检索增强生成
- [ ] 文本分块 chunking
- [ ] Embedding 原理
- [ ] 向量数据库（Chroma / pgvector）
- [ ] 完整 RAG 流程：入库→检索→拼 prompt→生成

### 第 11 周 — Agent 与编排
- [ ] LangChain / LlamaIndex 选学
- [ ] ReAct 模式、多步推理
- [ ] 记忆 memory

### 第 12 周 — 阶段项目
- [ ] **项目**：RAG 知识库问答应用
  - [ ] 文档上传 + 向量化
  - [ ] 检索 + 问答
  - [ ] 来源引用
  - [ ] 流式输出

> ✅ 通关：从零搭 RAG + 工具调用应用，并讲清每一步原理。

---

## P4 · 综合项目 + 上线（第 13-16 周）

- [ ] 第 13-14 周：选题 + 开发（建议结合前端背景：AI 代码助手 / 设计稿转代码 / 文档问答）
- [ ] 第 15 周：工程完善（流式 UI、降级、限流、可观测性、eval）
- [ ] 第 16 周：部署上线（Docker + Railway/Render/Fly.io + README + demo）

> ✅ 最终产出：可访问的全栈 AI 应用 + GitHub 仓库 + 部署链接。

---

## 求职作品集清单（同步积累）
- [ ] GitHub 持续提交
- [ ] 3 个阶段项目都有 README + demo
- [ ] 2-3 篇技术博客（RAG / Tool Calling / 部署踩坑）
- [ ] 一个可在线访问的 AI 应用
