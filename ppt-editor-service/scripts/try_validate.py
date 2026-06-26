import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.validate import validate_html, render_and_measure  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "sample_h5.html")
html = open(path, encoding="utf-8").read()

pages = render_and_measure(html)
print("=== render_and_measure: 顶层文档里找到的 section.slide 页数 ===")
print(len(pages))
print(json.dumps(pages, ensure_ascii=False)[:800])

print("\n=== validate_html 结果 ===")
print(json.dumps(validate_html(html), ensure_ascii=False, indent=2))
