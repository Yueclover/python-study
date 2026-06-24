# Frontend Slides 生成器(Dify Chatflow)

把 [frontend-slides](https://github.com/zarazhangrui/frontend-slides) 技能落成的 Dify
`advanced-chat` 应用:聊天框给出主题/大纲,流式输出一套零依赖、可直接保存为 `.html` 打开的
1920×1080 幻灯片,风格从 12 个预设里自动挑选。

## 文件
- `frontend-slides-chatflow.yml` —— 可导入 Dify 的 DSL(由构建脚本生成,勿手改)。
- `build_frontend_slides_chatflow.py` —— 构建脚本;改完提示词/模型后运行它重新生成 YAML。
- `frontend_slides_prompts.py` —— plan/render 两个系统提示词。
- `assets/frontend-slides/viewport-base.css` —— 上游固定 stage 样式(MIT,原样)。

## 重新生成 YAML
```bash
cd ppt-editor-service
python dify/build_frontend_slides_chatflow.py
```

## 导入 Dify
1. Dify 控制台 → 创建应用 → 导入 DSL → 选 `frontend-slides-chatflow.yml`。
2. 打开 `plan` 与 `render` 两个 LLM 节点,把模型换成你账号里可用的:
   - `plan`:快模型即可。
   - `render`:**选可用列表里最强的模型**(生成长 HTML 很吃能力)。
   - 默认填的是 `wxj/bifrost/bifrost` 的 `qwen3.6-plus`,按需替换。
3. 若改了 `frontend_slides_prompts.py`,先跑构建脚本再重新导入。

## 用法
直接发:`帮我做一套关于「2026 产品发布」的 8 页演示,正式一点`。
回复会是一段 ```html 代码块 —— 复制全部,存成 `deck.html`,浏览器打开即可:
方向键/空格/上下翻页、触摸滑动、滚轮翻页,整页 16:9 自适应缩放。

## 验收标准
- 导入无报错,4 节点 `start → plan → render → answer` 连通。
- 发一条需求,聊天框流式吐出完整 HTML。
- 存成 `.html` 打开:首页可见、按键能翻页、窗口缩放时整页等比缩放不变形。

## 范围(v1)
只做"从内容凭空生成";不含 PPT→HTML、不含服务端渲染校验回路。
