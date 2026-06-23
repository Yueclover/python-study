"""PPT HTML 渲染校验：检测单页内容溢出与文本重叠。"""

VIEWPORT = (960, 540)
OVERFLOW_TOL = 2.0      # px：超出页面边界的容差
OVERLAP_RATIO = 0.25    # 相交面积 / 两元素较小面积，超过即判重叠


def _overlap_ratio(a: dict, b: dict) -> float:
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    inter_w = max(0.0, min(ax2, bx2) - max(a["x"], b["x"]))
    inter_h = max(0.0, min(ay2, by2) - max(a["y"], b["y"]))
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    smaller = min(a["w"] * a["h"], b["w"] * b["h"])
    return inter / smaller if smaller > 0 else 0.0


def _max_overlap(leaves: list[dict]):
    """返回 (ratio, textA, textB)；无重叠返回 None。"""
    best = None
    for i in range(len(leaves)):
        for j in range(i + 1, len(leaves)):
            r = _overlap_ratio(leaves[i], leaves[j])
            if best is None or r > best[0]:
                best = (r, leaves[i].get("text", ""), leaves[j].get("text", ""))
    return best


def analyze_pages(pages: list[dict], overflow_tol: float = OVERFLOW_TOL,
                  overlap_ratio: float = OVERLAP_RATIO) -> list[dict]:
    bad = []
    for p in pages:
        right = float(p.get("overflow_right", 0) or 0)
        bottom = float(p.get("overflow_bottom", 0) or 0)
        of = max(right, bottom)
        if of > overflow_tol:
            label = "下" if bottom >= right else "右"
            bad.append({"page": p["page"], "type": "overflow",
                        "detail": f"{label}溢出约{round(of)}px"})
        best = _max_overlap(p.get("leaves", []) or [])
        if best is not None and best[0] > overlap_ratio:
            ratio, ta, tb = best
            bad.append({"page": p["page"], "type": "overlap",
                        "detail": f'文本重叠~{round(ratio * 100)}% ("{ta}" / "{tb}")'})
    return bad


# ---------------------------------------------------------------------------
# 浏览器渲染层（Playwright）
# ---------------------------------------------------------------------------

# 注入浏览器执行：逐 section 测量溢出量与文本叶子元素几何
MEASURE_JS = r"""
() => {
  const secs = Array.from(document.querySelectorAll('section.slide'));
  return secs.map((sec, i) => {
    const sr = sec.getBoundingClientRect();
    let page = i + 1;
    const m = (sec.id || '').match(/slide-(\d+)/);
    if (m) page = parseInt(m[1], 10);
    let overRight = 0, overBottom = 0;
    const leaves = [];
    sec.querySelectorAll('*').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width <= 0 && r.height <= 0) return;
      overRight = Math.max(overRight, r.right - sr.right);
      overBottom = Math.max(overBottom, r.bottom - sr.bottom);
      const txt = (el.textContent || '').trim();
      if (el.children.length === 0 && txt.length > 0 && r.width > 0 && r.height > 0) {
        leaves.push({x: r.left, y: r.top, w: r.width, h: r.height, text: txt.slice(0, 20)});
      }
    });
    return {page: page, overflow_right: overRight, overflow_bottom: overBottom, leaves: leaves};
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
            return page.evaluate(MEASURE_JS)
        finally:
            browser.close()


def validate_html(html: str) -> dict:
    try:
        pages = render_and_measure(html)
    except Exception as exc:  # fail-open：渲染异常不阻断出图
        return {"bad_pages": [], "error": str(exc)}
    return {"bad_pages": analyze_pages(pages)}
