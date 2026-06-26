"""手动验证 plan→/apply_plan：
PYTHONPATH=. python scripts/demo_plan.py input.pptx output.pptx
"""
import sys
from pptx import Presentation
from app.parser import parse_presentation
from app.plan import expand_plan
from app.applier import apply_ops


def main():
    src, dst = sys.argv[1], sys.argv[2]
    prs = Presentation(src)
    structure = parse_presentation(prs)
    first_slide = structure["slides"][0]["slide_id"]
    plan = [
        {"kind": "fill", "slide_id": first_slide,
         "fields": {structure["slides"][0]["shapes"][0]["shape_id"]: "PLAN 演示标题"}},
    ]
    ops, warnings = expand_plan(plan, structure)
    applied, rejected = apply_ops(prs, ops)
    prs.save(dst)
    print(f"ops={len(ops)} applied={applied} rejected={rejected} warnings={warnings} -> {dst}")


if __name__ == "__main__":
    main()
