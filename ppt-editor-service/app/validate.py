"""PPT HTML 渲染校验：检测每个 section 内容是否超出固定页面盒子（溢出）。"""

VIEWPORT = (960, 540)
OVERFLOW_TOL = 2.0      # px：超出页面边界的容差
FIT_SAFETY = 0.99       # 缩放系数安全余量，避免临界仍溢出


def analyze_pages(pages: list[dict], overflow_tol: float = OVERFLOW_TOL) -> list[dict]:
    bad = []
    for p in pages:
        overflows = {
            "上": float(p.get("overflow_top", 0) or 0),
            "下": float(p.get("overflow_bottom", 0) or 0),
            "左": float(p.get("overflow_left", 0) or 0),
            "右": float(p.get("overflow_right", 0) or 0),
        }
        label, of = max(overflows.items(), key=lambda item: item[1])
        if of > overflow_tol:
            bad.append({"page": p.get("page"), "type": "overflow",
                        "detail": f"{label}溢出约{round(of)}px"})
    return bad


# ---------------------------------------------------------------------------
# 浏览器渲染层（Playwright）
# ---------------------------------------------------------------------------

# 注入浏览器执行：逐 section 测量内容溢出量。
# 同时结合 scroll 尺寸与后代元素真实边界，避免漏掉绝对定位等脱离文档流的内容。
MEASURE_JS = r"""
({ selector }) => {
  const secs = Array.from(document.querySelectorAll(selector || 'section.slide'));
  const measureOverflow = (sec) => {
    const secRect = sec.getBoundingClientRect();
    let overflowRight = Math.max(0, sec.scrollWidth - sec.clientWidth);
    let overflowBottom = Math.max(0, sec.scrollHeight - sec.clientHeight);
    let overflowLeft = 0;
    let overflowTop = 0;

    const walker = document.createTreeWalker(sec, NodeFilter.SHOW_ELEMENT);
    while (walker.nextNode()) {
      const el = walker.currentNode;
      if (el === sec) continue;
      const style = window.getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') continue;

      const rects = Array.from(el.getClientRects());
      rects.forEach((rect) => {
        if (rect.width <= 0 && rect.height <= 0) return;
        overflowRight = Math.max(overflowRight, rect.right - secRect.right);
        overflowBottom = Math.max(overflowBottom, rect.bottom - secRect.bottom);
        overflowLeft = Math.max(overflowLeft, secRect.left - rect.left);
        overflowTop = Math.max(overflowTop, secRect.top - rect.top);
      });
    }

    return {
      overflow_top: Math.max(0, overflowTop),
      overflow_right: Math.max(0, overflowRight),
      overflow_bottom: Math.max(0, overflowBottom),
      overflow_left: Math.max(0, overflowLeft),
    };
  };

  return secs.map((sec, i) => {
    let page = i + 1;
    const m = (sec.id || '').match(/slide-(\d+)/);
    if (m) page = parseInt(m[1], 10);
    return {
      page: page,
      section_id: sec.id || null,
      ...measureOverflow(sec),
    };
  });
}
"""


def render_and_measure(html: str) -> list[dict]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]})
            page.set_content(html or "", wait_until="networkidle")
            page.wait_for_timeout(300)  # 等 srcdoc iframe 及页内自适应脚本执行
            # 部分产物把每页 section 包在 <iframe srcdoc> 里，需要逐 frame 测量后汇总
            pages = []
            for frame in page.frames:
                try:
                    # 抹掉宿主默认 body 边距/滚动条，避免把"页面没有内嵌 reset"
                    # 误判成右侧/底部溢出（裸 section 产物常见）
                    frame.add_style_tag(content=(
                        "html,body{margin:0!important;padding:0!important;}"
                        "html{overflow:hidden!important;}"
                        "*::before,*::after{content:none!important;}"  # 伪元素不参与溢出测量
                    ))
                    res = frame.evaluate(MEASURE_JS, {"selector": "section.slide"})
                except Exception:
                    continue
                if res:
                    pages.extend(res)
            return pages
        finally:
            browser.close()


_RESET_CSS = ("html,body{margin:0!important;padding:0!important;}"
              "html{overflow:hidden!important;}"
              "*::before,*::after{content:none!important;}")  # 伪元素不参与溢出测量


def check_section_overflow(
    html: str,
    selector: str = "section.slide",
    section_index: int = 0,
    overflow_tol: float = OVERFLOW_TOL,
) -> dict:
    """检查 HTML 中某个 section 的内容是否溢出其自身盒子。

    适用于整页 HTML，也适用于只传单个 ``section`` 片段。
    返回值中的 overflow_top / overflow_right / overflow_bottom / overflow_left
    为超出 section 上、右、下、左四边的像素值。
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]})
            page.set_content(html or "", wait_until="networkidle")
            page.wait_for_timeout(300)
            page.add_style_tag(content=_RESET_CSS)
            sections = page.evaluate(MEASURE_JS, {"selector": selector})
            if not sections or section_index >= len(sections):
                return {
                    "found": False,
                    "selector": selector,
                    "section_index": section_index,
                    "overflow": False,
                    "overflow_top": 0.0,
                    "overflow_right": 0.0,
                    "overflow_bottom": 0.0,
                    "overflow_left": 0.0,
                }

            section = sections[section_index]
            top = float(section.get("overflow_top", 0) or 0)
            right = float(section.get("overflow_right", 0) or 0)
            bottom = float(section.get("overflow_bottom", 0) or 0)
            left = float(section.get("overflow_left", 0) or 0)
            return {
                "found": True,
                "selector": selector,
                "section_index": section_index,
                "page": section.get("page"),
                "section_id": section.get("section_id"),
                "overflow": max(top, right, bottom, left) > overflow_tol,
                "overflow_top": top,
                "overflow_right": right,
                "overflow_bottom": bottom,
                "overflow_left": left,
            }
        finally:
            browser.close()


def validate_html(html: str) -> dict:
    try:
        pages = render_and_measure(html)
    except Exception as exc:  # fail-open：渲染异常不阻断出图
        return {"bad_pages": [], "error": str(exc)}
    return {"bad_pages": analyze_pages(pages)}


# 注入浏览器执行：对溢出的 section 等比缩放修复（保持 section 宽高不变）。
# 结构：section(固定画框) > outer(固定 box, overflow:hidden) > inner(自然高度, scale)。
#   - 测量缩放系数前临时关闭伪元素，避免装饰性 ::before/::after 把内容无谓缩小。
#   - inner 复用 section 的 class 继承 .slide 布局；outer 把布局溢出裁回，画框尺寸不变。
FIX_JS = r"""
(args) => {
  const tol = args[0], safety = args[1];
  const secs = Array.from(document.querySelectorAll('section.slide'));
  const fixed = [];
  secs.forEach((sec, i) => {
    let page = i + 1;
    const m = (sec.id || '').match(/slide-(\d+)/);
    if (m) page = parseInt(m[1], 10);
    const boxW = sec.clientWidth, boxH = sec.clientHeight;

    // 把内容搬进 inner（复用 .slide 布局，放开高度），先不缩放，量它的真实自然尺寸。
    // 绝对定位的装饰性伪元素不计入 offsetHeight，因此天然被忽略。
    const inner = document.createElement('div');
    inner.className = sec.className;
    inner.style.width = boxW + 'px';
    inner.style.height = 'auto';
    inner.style.minHeight = boxH + 'px';
    Array.from(sec.childNodes).forEach(n => {
      if (n.nodeType === 1 && n.tagName === 'STYLE') return;
      inner.appendChild(n);
    });
    const outer = document.createElement('div');
    outer.appendChild(inner);
    sec.appendChild(outer);
    const padBak = sec.style.padding;
    sec.style.padding = '0';

    const needW = inner.scrollWidth, needH = inner.offsetHeight;
    if (needW - boxW <= tol && needH - boxH <= tol) {
      // 无真实内容溢出（仅装饰等）：撤销改动，保持原样。
      while (inner.firstChild) sec.insertBefore(inner.firstChild, outer);
      sec.removeChild(outer);
      sec.style.padding = padBak;
      return;
    }

    const k = Math.min(1, Math.min(boxW / needW, boxH / needH) * safety);
    inner.style.transform = 'scale(' + k + ')';
    inner.style.transformOrigin = 'top center';
    outer.style.width = boxW + 'px';
    outer.style.height = boxH + 'px';
    outer.style.overflow = 'hidden';
    sec.style.overflow = 'hidden';
    sec.style.position = 'relative';
    fixed.push({page: page, scale: Math.round(k * 1000) / 1000});
  });
  return fixed;
}
"""


def repair_html(html: str) -> str:
    """对 section 内容溢出做等比缩放修复，返回修复后的完整 HTML。

    - 保持每个 section 宽高不变，仅把溢出内容整体缩放进画框。
    - 测量时忽略装饰性伪元素，无真实溢出时原样返回输入。
    - 仅处理主文档内的 section（iframe srcdoc 产物暂不处理）；渲染异常时原样返回。
    """
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]})
            page.set_content(html or "", wait_until="networkidle")
            page.wait_for_timeout(300)
            fixed = page.evaluate(FIX_JS, [OVERFLOW_TOL, FIT_SAFETY])
            if not fixed:
                return html
            return page.content()
        finally:
            browser.close()
