"""手动演示：python demo_roundtrip.py input.pptx output.pptx
仅改第一页第一个文本框，验证机械链路。"""
import sys
from pptx import Presentation
from app.parser import parse_presentation
from app.applier import apply_ops


def main():
    src, dst = sys.argv[1], sys.argv[2]
    prs = Presentation(src)
    doc = parse_presentation(prs)
    first = doc["slides"][0]["shapes"][0]["shape_id"]
    applied, rejected = apply_ops(prs, [
        {"op": "set_text", "shape_id": first, "text": "DEMO 改写成功"},
    ])
    prs.save(dst)
    print(f"applied={applied} rejected={rejected} -> {dst}")


if __name__ == "__main__":
    main()
