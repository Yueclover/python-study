# Frontend-Slides Chatflow 设计文档

- 日期:2026-06-24
- 分支:feat/ppt-editor-service
- 来源技能:[frontend-slides](https://github.com/zarazhangrui/frontend-slides)(MIT)

## 1. 目标

把 frontend-slides 技能"将内容生成零依赖单文件 HTML 演示"的能力,落成一个**全新**的 Dify
应用。用户在聊天框里给出主题/大纲/要点,应用直接在回复里**流式输出一份完整的、可直接保存为
`.html` 打开的幻灯片源码**。

这是与现有 `ppt-template-llm-edit.yml`(模板驱动、回写 pptx)**并列且独立**的另一条线,
不复用、不参考其图结构。

## 2. 已锁定的范围决策

| 维度 | 决策 |
|---|---|
| 应用形态 | Dify **Chatflow**(`mode: advanced-chat`) |
| 交付方式 | **聊天框流式输出完整 HTML 源码**(用 ```` ```html ```` 包裹) |
| 风格选择 | **全自动**——由 LLM 根据内容气质从 12 个预设里挑一个,不问用户 |
| 渲染校验回路 | **v1 不加**(`/validate` + 坏页改写留待后续) |
| 生成范围 | **只做"从内容凭空生成"**,不做 PPT→HTML 转换 |
| 实现方案 | **方案 B:两段式**(策划 → 生成),保留流式输出 |

### 被否决的备选

- **方案 A(单 LLM 一把梭)**:一个巨型提示词同时选风格+排内容+写全部页,长 deck 质量不稳、易截断。
- **方案 C(两段 + Code 拼装)**:样板由代码确定性注入虽然更稳,但末端 Code 拼装会**丢掉流式输出**
  (与主分支近期"恢复流式输出"的方向相悖),否决。

## 3. 架构

Dify `advanced-chat` 线性图,4 个节点:

```
开始(start) → LLM·策划(plan) → LLM·生成(render) → 直接回复(Answer)
```

每个节点单一职责、通过明确的数据契约衔接:

### ① 开始节点 start
- 主输入:`sys.query` —— 用户的主题 / 大纲 / 要点(自由文本)。
- 可选表单字段(默认值都体现"全自动"):
  - `density`:`auto | speaker-led | reading-first`,默认 `auto`。
  - `pages`:期望页数,数字,选填;留空 = 模型自定。

### ② LLM·策划节点 plan
- **职责**:理解需求 → 自动选定一个风格预设 → 产出逐页大纲。不写 HTML。
- **system prompt 内嵌**:
  - frontend-slides 的内容梳理规则(low/high density 两档的取舍);
  - **12 个风格预设清单**(名称 + 字体 + 配色 + 背景 + 动画基调,见附录 A);
  - 自动选风格规则:依据主题气质 / 受众 / 正式度挑最合适的一个,并给出该预设对应的
    Google Fonts、主色/底色/强调色。
- **输入**:`sys.query` + `density` + `pages`。
- **输出**:单段 JSON(纯文本,不带代码块包裹),契约:
  ```json
  {
    "style": "<预设名>",
    "theme": {
      "bg": "#...", "text": "#...", "accent": "#...",
      "display_font": "<字体名>", "body_font": "<字体名>",
      "google_fonts_url": "https://fonts.googleapis.com/..."
    },
    "density": "speaker-led | reading-first",
    "outline": [
      { "role": "cover|toc|section|content|table|ending", "title": "...", "points": ["..."] }
    ]
  }
  ```
- 参数:`temperature 0.2`,不流式。

### ③ LLM·生成节点 render
- **职责**:照固定脚手架把策划 JSON 渲染成**完整单文件 HTML**。
- **system prompt 内嵌**(作为**字面脚手架**,要求模型照抄、只改主题变量和正文):
  - 完整固定 HTML 骨架:`<!DOCTYPE html>` + `<head>`(原样内联 `viewport-base.css` +
    Google Fonts `<link>`)+ `<body>` + 末尾 `SlidePresentation` 导航 JS 类;
  - frontend-slides 视觉/动画/排版铁律:强排版(刻意字体)、承诺式配色(强主色 + 锐利强调色)、
    氛围式分层背景、编排式分阶动画(staggered reveal)、固定 1920×1080 stage、`.active`
    类控制可见性(不用 `display:none`)、`prefers-reduced-motion` 支持。
- **输入**:②的 JSON。
- **输出**:一份**完整 HTML**(照抄脚手架,改主题 CSS 变量 + 填 `<section class="slide">` 正文)。
- **此节点流式输出**。

### ④ 直接回复 Answer
- 引用 `{{#render.text#}}`,前置 ```` ```html ````、后置 ```` ``` ````,流式输出到聊天框。

## 4. 数据契约小结

- start → plan:`sys.query`(str)、`density`(枚举)、`pages`(number|空)。
- plan → render:第 3 节的 JSON。render 节点对该 JSON 做"尽力解析、字段缺失走默认"的
  fail-open 处理(与主分支 `analyze_pages` 的 fail-open 风格一致)。
- render → Answer:完整 HTML 字符串。

## 5. 错误处理

- **策划 JSON 不合法**:生成节点提示词要求"即使上游 JSON 不完整也要尽力产出合理幻灯片",
  不硬失败(fail-open)。
- **风格字段缺失**:生成节点回退到一个安全默认主题(深色 Bold Signal 系)。
- v1 不做服务端校验,渲染正确性由提示词铁律 + 固定脚手架保证。

## 6. 交付物

- 一个可导入 Dify 的 DSL:`ppt-editor-service/dify/frontend-slides-chatflow.yml`
  (`mode: advanced-chat`)。
- 不新增后端代码,不动 `ppt-editor-service/app/`。

## 7. 待办 / 实现期依赖

实现阶段需从 frontend-slides 仓库**原样拉取**并嵌入③的提示词:

- `viewport-base.css` 全文(固定 stage + `.slide`/`.active` 规则);
- `html-template.md` 里的 `SlidePresentation` 导航 JS(键盘/触摸/滚轮导航 + `setupStageScale`);
- `animation-patterns.md` 的分阶 reveal 动画要点。

## 8. 需用户拍板的配置项

- **模型 provider/model**:现有 Dify 装的是 `wxj/bifrost` 插件(qwen3.6-plus、minimax-m3 等)。
  生成长 HTML 很吃模型能力,**建议 render 节点用其中最强的模型**;plan 节点可用较快的模型。
  最终模型名在导入 Dify 后按可用列表确认。

## 附录 A:12 个风格预设(来自 STYLE_PRESETS.md)

深色:
1. **Bold Signal** — Archivo Black + Space Grotesk;#1a1a1a 底 / #FF5722 卡 / #fff 字;深色渐变上的彩色卡 + 大号分区编号。
2. **Electric Studio** — Manrope;#0a0a0a/#fff/#4361ee;双栏垂直分割 + 强调条。
3. **Creative Voltage** — Syne + Space Mono;#0066ff 蓝 / #d4ff00 霓虹黄 / #1a1a2e;电光蓝+霓虹黄对比 + 半调纹理。
4. **Dark Botanical** — Cormorant + IBM Plex Sans;#0f0f0f/#e8e4df/暖金粉;深色居中 + 柔和抽象渐变形。

浅色:
5. **Notebook Tabs** — Bodoni Moda + DM Sans;#2d2d2d 外 / #f8f6f1 页 / 多彩标签;暗底奶油卡 + 右缘彩色标签。
6. **Pastel Geometry** — Plus Jakarta Sans;#c8d9e6 底 / #faf9f7 卡 / 粉彩 pill;粉彩底白卡 + 高低不一竖条。
7. **Split Pastel** — Outfit;#f5e6dc 桃 / #e4dff0 薰衣草;双色垂直分割 + 网格叠层 + 圆角按钮。
8. **Vintage Editorial** — Fraunces + Work Sans;#f5f3ee 奶油 / #1a1a1a 字 / 暖强调;奶油底居中 + 抽象几何 CSS 形。

特色:
9. **Neon Cyber** — Clash Display + Satoshi;深蓝/青/品红;粒子效果。
10. **Terminal Green** — JetBrains Mono;#0d1117/#39d353;扫描线 + 光标。
11. **Swiss Modern** — Archivo + Nunito;白/黑/红;网格 + 非对称。
12. **Paper & Ink** — Cormorant Garamond + Source Serif 4;奶油/炭/绯红;首字下沉。
