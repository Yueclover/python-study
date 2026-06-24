# Frontend-Slides Chatflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 产出一个可导入 Dify 的 `advanced-chat`(Chatflow)DSL,聊天框里给出主题/大纲即流式输出一份零依赖、可直接保存为 `.html` 的 1920×1080 幻灯片源码,风格全自动从 12 个 frontend-slides 预设中选取。

**Architecture:** 用一个 Python 构建脚本确定性地拼装 Dify DSL(避免手写超长 YAML 的转义地狱)。两个系统提示词(plan / render)放在独立模块里作为字符串常量;render 提示词把 vendored 的 `viewport-base.css` 原样内联进固定 HTML 脚手架。图为线性 4 节点:`start → LLM·plan → LLM·render → answer`。所有校验用 pytest 跑在「构建出的 dict / YAML」上;最终验收 = 导入 Dify 跑通。

**Tech Stack:** Python 3、PyYAML、pytest;Dify `advanced-chat` DSL;frontend-slides(MIT)素材。

## Global Constraints

- Dify 应用模式必须为 `advanced-chat`(`app.mode: advanced-chat`,`kind: app`)。
- 图严格线性 4 节点:`start → plan → render → answer`,节点 `type: custom`,边 `type: custom`、`sourceHandle: source`、`targetHandle: target`。
- 最终交付物 YAML:`ppt-editor-service/dify/frontend-slides-chatflow.yml`。
- **不改动** `ppt-editor-service/app/` 下任何后端代码;不复用 `ppt-template-llm-edit.yml` 的图。
- 风格**全自动**:plan 节点从 12 个预设里挑且仅挑一个,不问用户。
- v1 **不含** `/validate` 校验回路、**不含** PPT→HTML 转换。
- 生成的 HTML 必须:单文件零依赖、固定 1920×1080 stage、用 `.active`/`.visible` 控制可见性(不用 `display:none`)、含 `@media (prefers-reduced-motion: reduce)`、字体走 Google Fonts/Fontshare(不用系统字体)。
- 12 个预设名称(verbatim):Bold Signal、Electric Studio、Creative Voltage、Dark Botanical、Notebook Tabs、Pastel Geometry、Split Pastel、Vintage Editorial、Neon Cyber、Terminal Green、Swiss Modern、Paper & Ink。
- 所有命令在 `ppt-editor-service/` 目录下运行;测试文件放 `tests/`。

---

### Task 1: Vendor 上游素材 + 出处声明

把 frontend-slides 的 `viewport-base.css` 原样落地到仓库,作为 render 提示词的 source-of-truth 与防漂移基准。

**Files:**
- Create: `ppt-editor-service/dify/assets/frontend-slides/viewport-base.css`
- Create: `ppt-editor-service/dify/assets/frontend-slides/SOURCE.md`
- Test: `ppt-editor-service/tests/test_frontend_slides_chatflow.py`

**Interfaces:**
- Produces: 一个可被后续构建脚本 `Path(...).read_text(encoding="utf-8")` 读取的 CSS 文件;不变量标记 `.deck-stage`、`width: 1920px`、`.slide.active`、`prefers-reduced-motion`。

- [ ] **Step 1: 写失败测试**

新建 `ppt-editor-service/tests/test_frontend_slides_chatflow.py`:

```python
from pathlib import Path

DIFY = Path(__file__).resolve().parent.parent / "dify"
CSS = DIFY / "assets" / "frontend-slides" / "viewport-base.css"


def test_vendored_css_present_and_intact():
    assert CSS.is_file(), f"缺少 vendored CSS: {CSS}"
    text = CSS.read_text(encoding="utf-8")
    for marker in [".deck-stage", "width: 1920px", ".slide.active", "prefers-reduced-motion"]:
        assert marker in text, f"viewport-base.css 缺少不变量: {marker}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: FAIL —— `缺少 vendored CSS`(文件还不存在)。

- [ ] **Step 3: 落地 CSS(原样)**

把下列内容**逐字**写入 `ppt-editor-service/dify/assets/frontend-slides/viewport-base.css`:

```css
/* ===========================================
   FIXED 16:9 STAGE: MANDATORY BASE STYLES
   Include this ENTIRE file in every presentation.
   Slides are authored at 1920×1080 and scaled as a whole.
   =========================================== */

/* 1. Lock the browser viewport */
html,
body {
    width: 100%;
    height: 100%;
    margin: 0;
    overflow: hidden;
    background: var(--stage-bg, #000);
}

/* 2. Full-window deck viewport */
.deck-viewport {
    position: fixed;
    inset: 0;
    overflow: hidden;
    background: var(--stage-bg, #000);
}

/* 3. Fixed 16:9 design canvas.
   JavaScript sets transform: translate(...) scale(...). */
.deck-stage {
    position: absolute;
    left: 0;
    top: 0;
    width: 1920px;
    height: 1080px;
    overflow: hidden;
    transform-origin: 0 0;
    background: var(--slide-bg, #fff);
}

/* 4. Slides stack inside the fixed stage.
   Content must be laid out at 1920×1080, not reflowed per device. */
.slide {
    position: absolute;
    inset: 0;
    width: 1920px;
    height: 1080px;
    overflow: hidden;
    display: block;
    visibility: hidden;
    opacity: 0;
    pointer-events: none;
    background: var(--slide-bg, #fff);
}

.slide.active,
.slide.visible {
    visibility: visible;
    opacity: 1;
    pointer-events: auto;
    z-index: 1;
}

/* 5. Keep media inside authored slide bounds */
img,
video,
canvas,
svg {
    max-width: 100%;
    max-height: 100%;
}

/* 6. Presentation chrome stays outside the slide design system */
.deck-controls {
    position: fixed;
    left: 50%;
    bottom: 22px;
    transform: translateX(-50%);
    z-index: 1000;
}

/* 7. Print one fixed-size slide per page */
@media print {
    html,
    body {
        width: 1920px;
        height: auto;
        overflow: visible;
        background: #fff;
    }

    .deck-viewport {
        position: static;
        overflow: visible;
        background: #fff;
    }

    .deck-stage {
        position: static;
        width: auto;
        height: auto;
        transform: none !important;
        background: none;
    }

    .slide {
        position: relative;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        width: 1920px;
        height: 1080px;
        break-after: page;
        page-break-after: always;
    }

    .slide:last-child {
        break-after: auto;
        page-break-after: auto;
    }

    .deck-controls {
        display: none !important;
    }
}

/* 8. Reduced motion */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.2s !important;
    }
}
```

写 `ppt-editor-service/dify/assets/frontend-slides/SOURCE.md`:

```markdown
# Vendored frontend-slides assets

- Upstream: https://github.com/zarazhangrui/frontend-slides
- File: `viewport-base.css`(原样,未改动)
- License: MIT
- 取用日期: 2026-06-24

用途:作为本目录 chatflow 中 render 提示词内联的固定 16:9 stage 基础样式 source-of-truth。
更新方式:`curl -s https://raw.githubusercontent.com/zarazhangrui/frontend-slides/main/viewport-base.css -o viewport-base.css`
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: PASS(1 passed)。

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/dify/assets/frontend-slides/ ppt-editor-service/tests/test_frontend_slides_chatflow.py
git commit -m "feat(dify): vendor frontend-slides viewport-base.css + provenance"
```

---

### Task 2: 两个系统提示词模块

把 plan / render 两个系统提示词作为字符串常量集中到一个模块,render 提示词在运行时把 vendored CSS 注入固定脚手架。与图构建逻辑分离(单一职责)。

**Files:**
- Create: `ppt-editor-service/dify/frontend_slides_prompts.py`
- Test: `ppt-editor-service/tests/test_frontend_slides_chatflow.py`(追加)

**Interfaces:**
- Produces:
  - `PLAN_SYSTEM_PROMPT: str` —— 含全部 12 个预设名 + JSON 契约键(`style`/`theme`/`density`/`outline`/`role`)。
  - `build_render_system_prompt() -> str` —— 读取 vendored `viewport-base.css` 并注入脚手架,返回完整 render 系统提示词;含 `SlidePresentation`、`setupStageScale`、`.active`、`prefers-reduced-motion`、fail-open 指令、"只输出 HTML"指令。
- Consumes: Task 1 的 `dify/assets/frontend-slides/viewport-base.css`。

- [ ] **Step 1: 写失败测试(追加到测试文件末尾)**

```python
import importlib.util

PROMPTS = DIFY / "frontend_slides_prompts.py"
PRESET_NAMES = [
    "Bold Signal", "Electric Studio", "Creative Voltage", "Dark Botanical",
    "Notebook Tabs", "Pastel Geometry", "Split Pastel", "Vintage Editorial",
    "Neon Cyber", "Terminal Green", "Swiss Modern", "Paper & Ink",
]


def _load_prompts():
    spec = importlib.util.spec_from_file_location("fs_prompts", PROMPTS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_plan_prompt_lists_all_presets_and_contract():
    mod = _load_prompts()
    p = mod.PLAN_SYSTEM_PROMPT
    for name in PRESET_NAMES:
        assert name in p, f"plan 提示词缺少预设: {name}"
    for key in ['"style"', '"theme"', '"density"', '"outline"', '"role"']:
        assert key in p, f"plan 提示词缺少 JSON 契约键: {key}"


def test_render_prompt_inlines_css_and_rules():
    mod = _load_prompts()
    r = mod.build_render_system_prompt()
    css = CSS.read_text(encoding="utf-8")
    # 证明 CSS 被原样内联
    for marker in [".deck-stage", ".slide.active", "prefers-reduced-motion"]:
        assert marker in r
    assert "width: 1920px" in r
    # 脚手架与铁律
    for token in ["SlidePresentation", "setupStageScale", "<!DOCTYPE html>"]:
        assert token in r, f"render 提示词缺少脚手架标记: {token}"
    # fail-open 与"只输出 HTML"
    assert "尽力" in r
    assert "只输出" in r or "只返回" in r
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: FAIL —— `No module named` / 文件不存在。

- [ ] **Step 3: 写提示词模块**

新建 `ppt-editor-service/dify/frontend_slides_prompts.py`:

```python
"""frontend-slides Chatflow 的两个系统提示词。

PLAN_SYSTEM_PROMPT      —— plan 节点:理解需求 → 自动选风格 → 产出逐页大纲 JSON。
build_render_system_prompt() —— render 节点:把大纲 JSON 渲染成完整单文件 HTML。
"""
from pathlib import Path

_CSS_PATH = Path(__file__).resolve().parent / "assets" / "frontend-slides" / "viewport-base.css"


PLAN_SYSTEM_PROMPT = """你是幻灯片策划师。根据用户需求,自动选定一种视觉风格,并规划逐页大纲。
只输出一段 JSON,不要解释、不要用代码块包裹。

## 可选风格预设(12 选 1,依据主题气质/受众/正式度自动挑最合适的一个)
深色:
- Bold Signal:Archivo Black+Space Grotesk;#1a1a1a 底/#FF5722 卡/#fff 字;深色渐变上的彩色卡+大号分区编号。
- Electric Studio:Manrope;#0a0a0a/#fff/#4361ee;双栏垂直分割+强调条。
- Creative Voltage:Syne+Space Mono;#0066ff/#d4ff00/#1a1a2e;电光蓝+霓虹黄对比+半调纹理。
- Dark Botanical:Cormorant+IBM Plex Sans;#0f0f0f/#e8e4df/暖金粉;深色居中+柔和抽象渐变形。
浅色:
- Notebook Tabs:Bodoni Moda+DM Sans;#2d2d2d/#f8f6f1/多彩标签;暗底奶油卡+右缘彩色标签。
- Pastel Geometry:Plus Jakarta Sans;#c8d9e6/#faf9f7/粉彩 pill;粉彩底白卡+高低不一竖条。
- Split Pastel:Outfit;#f5e6dc/#e4dff0;双色垂直分割+网格叠层+圆角按钮。
- Vintage Editorial:Fraunces+Work Sans;#f5f3ee/#1a1a1a/暖强调;奶油底居中+抽象几何 CSS 形。
特色:
- Neon Cyber:Clash Display+Satoshi;深蓝/青/品红;粒子效果。
- Terminal Green:JetBrains Mono;#0d1117/#39d353;扫描线+光标。
- Swiss Modern:Archivo+Nunito;白/黑/红;网格+非对称。
- Paper & Ink:Cormorant Garamond+Source Serif 4;奶油/炭/绯红;首字下沉。

## 密度
- speaker-led(演讲型):一页一个观点,留白多,1-3 条要点。
- reading-first(阅读型):结构化网格/表格,4-8 条要点/卡片,信息自洽。
若用户给了 density 就用它;为 auto 时你自行判断。

## role 取值
cover / toc / section / content / table / ending。

## 输出契约(严格,只输出这段 JSON)
{
  "style": "<上面 12 个预设名之一>",
  "theme": {
    "bg": "#...", "text": "#...", "accent": "#...",
    "display_font": "<标题字体名>", "body_font": "<正文字体名>",
    "google_fonts_url": "https://fonts.googleapis.com/css2?family=...&display=swap"
  },
  "density": "speaker-led | reading-first",
  "outline": [
    {"role": "cover", "title": "主标题", "points": ["副标题/作者"]},
    {"role": "content", "title": "本页标题", "points": ["要点1", "要点2"]}
  ]
}

规则:
1. style 必须严格等于 12 个预设名之一;theme 的字体与配色要与该预设一致。
2. google_fonts_url 要能真实加载 display_font 与 body_font。
3. outline 顺序即最终页序;封面/目录/正文/结尾齐全。
4. points 要具体、可直接据此写文案。
"""


_RENDER_SCAFFOLD = """## 必须照抄的固定 HTML 脚手架
输出一份完整文件,结构如下;{{CSS}} 处已是固定基础样式,原样保留:

<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>(用封面标题)</title>
<link rel="stylesheet" href="(plan 给的 google_fonts_url)">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  /* 用 plan.theme 填充 */
  --stage-bg: <theme.bg>;
  --slide-bg: <theme.bg>;
  --text-primary: <theme.text>;
  --accent: <theme.accent>;
  --font-display: <theme.display_font>, sans-serif;
  --font-body: <theme.body_font>, sans-serif;
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-normal: 0.6s;
}

/* >>> 固定基础样式(原样,不要改) <<< */
{{CSS}}
/* <<< 固定基础样式结束 >>> */

/* 入场动画:由 .slide.visible 触发,逐项 stagger */
.reveal { opacity: 0; transform: translateY(30px);
  transition: opacity var(--duration-normal) var(--ease-out-expo),
              transform var(--duration-normal) var(--ease-out-expo); }
.slide.visible .reveal { opacity: 1; transform: translateY(0); }
.reveal:nth-child(1){transition-delay:.1s} .reveal:nth-child(2){transition-delay:.2s}
.reveal:nth-child(3){transition-delay:.3s} .reveal:nth-child(4){transition-delay:.4s}

/* 这里追加所选预设的专属样式(配色块、排版、氛围背景等) */
</style>
</head>
<body>
<div class="deck-viewport">
  <main class="deck-stage" id="deckStage">
    <!-- 按 outline 逐页输出 <section class="slide ...">;第一页加 active visible -->
  </main>
</div>
<div class="deck-controls"><span id="pageNum"></span></div>
<script>
class SlidePresentation {
  constructor(){
    this.slides=document.querySelectorAll('.slide');
    this.i=0; this.stage=document.getElementById('deckStage');
    this.setupStageScale(); this.setupNav(); this.show(0);
  }
  setupStageScale(){
    const s=()=>{const f=Math.min(innerWidth/1920,innerHeight/1080);
      const x=(innerWidth-1920*f)/2, y=(innerHeight-1080*f)/2;
      this.stage.style.transform=`translate(${x}px,${y}px) scale(${f})`;};
    s(); addEventListener('resize', s);
  }
  setupNav(){
    addEventListener('keydown',e=>{
      if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();this.show(this.i+1);}
      if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();this.show(this.i-1);}
    });
    let x0=null;
    addEventListener('touchstart',e=>x0=e.touches[0].clientX,{passive:true});
    addEventListener('touchend',e=>{if(x0===null)return;const dx=e.changedTouches[0].clientX-x0;
      if(Math.abs(dx)>40)this.show(this.i+(dx<0?1:-1));x0=null;});
    let lock=false;
    addEventListener('wheel',e=>{if(lock)return;lock=true;setTimeout(()=>lock=false,400);
      this.show(this.i+(e.deltaY>0?1:-1));},{passive:true});
  }
  show(n){
    this.i=Math.max(0,Math.min(n,this.slides.length-1));
    this.slides.forEach((s,k)=>{const on=k===this.i;
      s.classList.toggle('active',on); s.classList.toggle('visible',on);});
    const el=document.getElementById('pageNum');
    if(el)el.textContent=(this.i+1)+' / '+this.slides.length;
  }
}
new SlidePresentation();
</script>
</body>
</html>
"""


_RENDER_RULES = """你是幻灯片 HTML 生成器。给定一段大纲 JSON(含 style/theme/density/outline),
生成一份完整、自包含、零依赖、可直接保存为 .html 打开的演示文件。

铁律:
1. **照抄上面的固定脚手架**,只改 :root 主题变量、追加所选预设专属样式、按 outline 填 <section class="slide"> 正文与导航逻辑,不要删改固定基础样式与 SlidePresentation 控制器。
2. 视觉:承诺式配色(强主色+锐利强调色,不要怯生生的平均分布)、刻意的字体层级、氛围式分层背景(多重 radial-gradient/网格/噪点);每页内容在 1920×1080 内排版,不做按设备 reflow。
3. 动画:编排式分阶 reveal,给关键元素加 class="reveal";避免零散微交互。
4. 每页 <section class="slide"> 贴合其 role(cover 写大标题副标题、toc 写目录条目、content 写要点、ending 收尾);第一页加 class="slide ... active visible"。
5. 可访问性:语义化标签;保留 prefers-reduced-motion(已在基础样式内)。
6. 字体只走 link 里的 Google Fonts/Fontshare,不用系统字体。
7. fail-open:即使大纲 JSON 不完整或字段缺失,也要尽力产出一份合理、不报错的演示;风格字段缺失时回退到深色 Bold Signal 系默认主题。

输出要求:**只输出最终 HTML 全文**,从 <!DOCTYPE html> 开始,不要任何解释、不要 markdown 代码块包裹。
"""


def build_render_system_prompt() -> str:
    css = _CSS_PATH.read_text(encoding="utf-8")
    scaffold = _RENDER_SCAFFOLD.replace("{{CSS}}", css)
    return _RENDER_RULES + "\n\n" + scaffold
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: PASS(3 passed)。

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/dify/frontend_slides_prompts.py ppt-editor-service/tests/test_frontend_slides_chatflow.py
git commit -m "feat(dify): plan/render system prompts for frontend-slides chatflow"
```

---

### Task 3: 构建脚本 —— 生成 advanced-chat DSL

写确定性构建脚本,拼出完整 4 节点线性图并 `yaml.dump` 到交付物 YAML。

**Files:**
- Create: `ppt-editor-service/dify/build_frontend_slides_chatflow.py`
- Create(脚本产物): `ppt-editor-service/dify/frontend-slides-chatflow.yml`
- Test: `ppt-editor-service/tests/test_frontend_slides_chatflow.py`(追加)

**Interfaces:**
- Consumes: Task 2 的 `PLAN_SYSTEM_PROMPT` 与 `build_render_system_prompt()`。
- Produces:
  - `build_app() -> dict` —— 返回完整 Dify DSL 字典。
  - `MODEL_PROVIDER = "wxj/bifrost/bifrost"`、`PLAN_MODEL`、`RENDER_MODEL` 常量(用户可改)。
  - 运行 `python dify/build_frontend_slides_chatflow.py` 写出 `dify/frontend-slides-chatflow.yml`。
  - 图中 node id:`start` / `plan` / `render` / `answer`;边按 `source-target` 命名。

- [ ] **Step 1: 写失败测试(追加)**

```python
import yaml

BUILD = DIFY / "build_frontend_slides_chatflow.py"
YML = DIFY / "frontend-slides-chatflow.yml"


def _load_build():
    spec = importlib.util.spec_from_file_location("fs_build", BUILD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nodes(app):
    return {n["id"]: n for n in app["workflow"]["graph"]["nodes"]}


def _edges(app):
    return {(e["source"], e["target"]) for e in app["workflow"]["graph"]["edges"]}


def test_app_is_advanced_chat_with_four_linear_nodes():
    app = _load_build().build_app()
    assert app["app"]["mode"] == "advanced-chat"
    assert app["kind"] == "app"
    nodes = _nodes(app)
    assert set(nodes) == {"start", "plan", "render", "answer"}
    assert nodes["start"]["data"]["type"] == "start"
    assert nodes["plan"]["data"]["type"] == "llm"
    assert nodes["render"]["data"]["type"] == "llm"
    assert nodes["answer"]["data"]["type"] == "answer"
    assert _edges(app) == {("start", "plan"), ("plan", "render"), ("render", "answer")}


def test_nodes_wire_prompts_and_streaming_answer():
    mod = _load_build()
    app = mod.build_app()
    nodes = _nodes(app)
    # plan 节点挂 plan 提示词,user 引用 sys.query
    plan_sys = nodes["plan"]["data"]["prompt_template"][0]["text"]
    assert "Bold Signal" in plan_sys and '"outline"' in plan_sys
    plan_user = nodes["plan"]["data"]["prompt_template"][1]["text"]
    assert "{{#sys.query#}}" in plan_user
    # render 节点挂 render 提示词(含内联 CSS),user 引用 plan.text
    render_sys = nodes["render"]["data"]["prompt_template"][0]["text"]
    assert ".deck-stage" in render_sys and "SlidePresentation" in render_sys
    render_user = nodes["render"]["data"]["prompt_template"][1]["text"]
    assert "{{#plan.text#}}" in render_user
    # answer 用 ```html 包裹 render 输出(保留流式)
    ans = nodes["answer"]["data"]["answer"]
    assert "```html" in ans and "{{#render.text#}}" in ans


def test_build_writes_loadable_yaml(tmp_path):
    mod = _load_build()
    app = mod.build_app()
    out = tmp_path / "out.yml"
    out.write_text(yaml.safe_dump(app, allow_unicode=True, sort_keys=False), encoding="utf-8")
    reloaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert reloaded["app"]["mode"] == "advanced-chat"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: FAIL —— 无法加载 `build_frontend_slides_chatflow`。

- [ ] **Step 3: 写构建脚本**

新建 `ppt-editor-service/dify/build_frontend_slides_chatflow.py`:

```python
"""确定性拼装 frontend-slides Chatflow 的 Dify advanced-chat DSL。

用法:
    python dify/build_frontend_slides_chatflow.py
会(重新)生成 dify/frontend-slides-chatflow.yml。
"""
import importlib.util
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent


def _load_prompts():
    spec = importlib.util.spec_from_file_location(
        "fs_prompts", _HERE / "frontend_slides_prompts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# —— 模型配置(用户按 Dify 内可用模型自行修改)——
MODEL_PROVIDER = "wxj/bifrost/bifrost"
PLAN_MODEL = "qwen3.6-plus"      # 策划:快即可
RENDER_MODEL = "qwen3.6-plus"    # 生成长 HTML:建议换成可用列表里最强的模型


def _llm_node(node_id, title, model, system_text, user_text, x):
    return {
        "id": node_id,
        "type": "custom",
        "width": 242, "height": 98,
        "position": {"x": x, "y": 100},
        "positionAbsolute": {"x": x, "y": 100},
        "selected": False,
        "sourcePosition": "right", "targetPosition": "left",
        "data": {
            "type": "llm", "title": title, "desc": "", "selected": False,
            "context": {"enabled": False, "variable_selector": []},
            "vision": {"enabled": False},
            "model": {
                "provider": MODEL_PROVIDER, "name": model, "mode": "chat",
                "completion_params": {"temperature": 0.2},
            },
            "prompt_template": [
                {"role": "system", "text": system_text},
                {"role": "user", "text": user_text},
            ],
        },
    }


def build_app() -> dict:
    prompts = _load_prompts()

    start = {
        "id": "start", "type": "custom",
        "width": 242, "height": 116,
        "position": {"x": 0, "y": 100},
        "positionAbsolute": {"x": 0, "y": 100},
        "selected": False, "sourcePosition": "right", "targetPosition": "left",
        "data": {
            "type": "start", "title": "开始", "desc": "", "selected": False,
            "variables": [
                {
                    "variable": "density", "label": "密度", "type": "select",
                    "required": False, "options": ["auto", "speaker-led", "reading-first"],
                    "default": "auto", "max_length": 48,
                },
                {
                    "variable": "pages", "label": "期望页数(选填)", "type": "number",
                    "required": False, "options": [],
                },
            ],
        },
    }

    plan_user = (
        "用户需求:\n{{#sys.query#}}\n\n"
        "密度:{{#start.density#}};期望页数:{{#start.pages#}}\n\n"
        "请只输出大纲 JSON。"
    )
    plan = _llm_node("plan", "策划", PLAN_MODEL,
                     prompts.PLAN_SYSTEM_PROMPT, plan_user, x=300)

    render_user = "大纲 JSON:\n{{#plan.text#}}\n\n请只输出最终 HTML 全文。"
    render = _llm_node("render", "生成", RENDER_MODEL,
                       prompts.build_render_system_prompt(), render_user, x=600)
    # 生成长 HTML,放宽采样
    render["data"]["model"]["completion_params"]["temperature"] = 0.4

    answer = {
        "id": "answer", "type": "custom",
        "width": 242, "height": 116,
        "position": {"x": 900, "y": 100},
        "positionAbsolute": {"x": 900, "y": 100},
        "selected": False, "sourcePosition": "right", "targetPosition": "left",
        "data": {
            "type": "answer", "title": "直接回复", "desc": "", "selected": False,
            "answer": "```html\n{{#render.text#}}\n```",
            "variables": [],
        },
    }

    def edge(src, dst):
        return {
            "id": f"{src}-{dst}", "source": src, "target": dst,
            "sourceHandle": "source", "targetHandle": "target",
            "type": "custom", "selected": False,
            "data": {"sourceType": "custom", "targetType": "custom", "isInLoop": False},
        }

    return {
        "app": {
            "name": "Frontend Slides 生成器",
            "description": "聊天给出主题/大纲,流式输出零依赖单文件 HTML 幻灯片(自动选风格)。",
            "mode": "advanced-chat",
            "icon": "🎬", "icon_background": "#1a1a1a", "icon_type": "emoji",
            "use_icon_as_answer_icon": False,
        },
        "kind": "app",
        "version": "0.6.0",
        "dependencies": [],
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {
                "file_upload": {"enabled": False},
                "opening_statement": "给我主题或大纲,我直接生成一套可保存为 .html 的幻灯片源码。",
                "retriever_resource": {"enabled": False},
                "sensitive_word_avoidance": {"enabled": False},
                "speech_to_text": {"enabled": False},
                "suggested_questions": [],
                "suggested_questions_after_answer": {"enabled": False},
                "text_to_speech": {"enabled": False, "language": "", "voice": ""},
            },
            "graph": {
                "nodes": [start, plan, render, answer],
                "edges": [edge("start", "plan"), edge("plan", "render"), edge("render", "answer")],
                "viewport": {"x": 0, "y": 0, "zoom": 0.8},
            },
            "rag_pipeline_variables": [],
        },
    }


def main():
    app = build_app()
    out = _HERE / "frontend-slides-chatflow.yml"
    out.write_text(
        yaml.safe_dump(app, allow_unicode=True, sort_keys=False, width=4096),
        encoding="utf-8",
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: PASS(6 passed)。

- [ ] **Step 5: 生成 YAML 交付物**

Run: `python dify/build_frontend_slides_chatflow.py`
Expected: 打印 `wrote .../dify/frontend-slides-chatflow.yml`,文件生成。

- [ ] **Step 6: 提交**

```bash
git add ppt-editor-service/dify/build_frontend_slides_chatflow.py ppt-editor-service/dify/frontend-slides-chatflow.yml ppt-editor-service/tests/test_frontend_slides_chatflow.py
git commit -m "feat(dify): build script + generated frontend-slides advanced-chat DSL"
```

---

### Task 4: 端到端结构校验(对生成的 YAML)

新增一个直接对**已生成的** `frontend-slides-chatflow.yml` 跑的测试,确保交付物本身(而非仅 build_app 字典)结构正确、且与 build 同步(防手改漂移)。

**Files:**
- Test: `ppt-editor-service/tests/test_frontend_slides_chatflow.py`(追加)

**Interfaces:**
- Consumes: Task 3 生成的 `dify/frontend-slides-chatflow.yml` 与 `build_app()`。

- [ ] **Step 1: 写失败测试(追加)**

```python
def test_generated_yaml_exists_and_matches_build():
    assert YML.is_file(), "请先运行 build 脚本生成 YAML"
    on_disk = yaml.safe_load(YML.read_text(encoding="utf-8"))
    fresh = _load_build().build_app()
    assert on_disk == fresh, "YAML 与 build_app() 不一致,请重新运行 build 脚本"
    # 关键交付契约
    assert on_disk["app"]["mode"] == "advanced-chat"
    ids = {n["id"] for n in on_disk["workflow"]["graph"]["nodes"]}
    assert ids == {"start", "plan", "render", "answer"}
```

- [ ] **Step 2: 跑测试**

Run: `python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: 若 Task 3 Step 5 已生成 YAML → PASS(7 passed);若漂移 → FAIL 提示重新 build。

- [ ] **Step 3:(如失败)重新生成并复跑**

Run: `python dify/build_frontend_slides_chatflow.py && python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: PASS(7 passed)。

- [ ] **Step 4: 提交**

```bash
git add ppt-editor-service/tests/test_frontend_slides_chatflow.py
git commit -m "test(dify): assert generated YAML matches build output"
```

---

### Task 5: 导入与验收文档

写使用说明:如何导入 Dify、改模型、怎么用、验收标准。

**Files:**
- Create: `ppt-editor-service/dify/README-frontend-slides.md`

**Interfaces:** 无代码接口。

- [ ] **Step 1: 写 README**

新建 `ppt-editor-service/dify/README-frontend-slides.md`:

```markdown
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
```

- [ ] **Step 2: 跑全量测试确保未回归**

Run: `python -m pytest tests/test_frontend_slides_chatflow.py -q`
Expected: PASS(7 passed)。

- [ ] **Step 3: 提交**

```bash
git add ppt-editor-service/dify/README-frontend-slides.md
git commit -m "docs(dify): frontend-slides chatflow import & acceptance guide"
```

---

## 验收(用户手动,需 Dify 环境)

1. `python dify/build_frontend_slides_chatflow.py` 重新生成 YAML。
2. 导入 Dify;把 `render` 模型换成最强可用模型。
3. 发一条需求 → 复制输出的 HTML → 存 `deck.html` → 浏览器打开。
4. 确认:首页可见、键盘/触摸/滚轮翻页、窗口缩放整页等比、风格符合预设。

## Self-Review(写计划者自检结论)

- **Spec 覆盖**:Chatflow(Task 3)、流式 HTML 输出(Task 3 answer ```html)、全自动选风格(Task 2 plan 提示词,Task 1/2 测试)、不加校验回路 & 只凭空生成(Global Constraints + 未建任何 http/validate 节点)、12 预设(Global Constraints + Task 2 测试)、viewport-base.css 内联(Task 1/2)、模型可配置项(Task 3 常量 + Task 5 README)——均有对应任务。
- **占位符**:无 TBD/TODO;每个代码步骤含完整可运行内容。
- **类型一致**:node id `start/plan/render/answer`、变量引用 `{{#sys.query#}}`/`{{#start.density#}}`/`{{#start.pages#}}`/`{{#plan.text#}}`/`{{#render.text#}}` 在构建脚本与测试间一致;`build_app()` 单一来源,Task 4 校验产物与之一致。
- **已知风险**:Dify `advanced-chat` 的精确 DSL schema 以本地无法跑通,最终以「导入 Dify」为验收(已在验收章节标注);若某字段被 Dify 拒收,按导入报错微调 `build_app()` 后重跑构建脚本即可,不影响整体结构。
```
