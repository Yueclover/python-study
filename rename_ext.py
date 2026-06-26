"""把指定文件夹下所有文件的后缀名临时改为 .json，之后再恢复原样。

用法：
    # 把 <dir> 下所有文件改成 .json（会生成 .rename_map.json 记录映射）
    python rename_ext.py to-json <dir>

    # 根据映射文件把它们恢复成原来的后缀
    python rename_ext.py restore <dir>

说明：
    - 改名时把「新文件名 -> 原文件名」写进 <dir>/.rename_map.json。
    - 恢复时读取该映射逐个还原，并删除映射文件。
    - 默认只处理 <dir> 第一层文件，不递归子目录；加 -r/--recursive 递归。
"""
import argparse
import json
import sys
from pathlib import Path

MAP_NAME = ".rename_map.json"


def iter_files(root: Path, recursive: bool):
    it = root.rglob("*") if recursive else root.iterdir()
    for p in it:
        if p.is_file() and p.name != MAP_NAME:
            yield p


def to_json(root: Path, recursive: bool) -> None:
    map_path = root / MAP_NAME
    if map_path.exists():
        sys.exit(f"已存在 {MAP_NAME}，请先 restore 再重试。")

    mapping = {}
    for p in iter_files(root, recursive):
        new_path = p.with_suffix(".json")
        # 避免重名覆盖
        i = 1
        while new_path.exists() or str(new_path.relative_to(root)) in mapping:
            new_path = p.with_name(f"{p.stem}_{i}.json")
            i += 1
        p.rename(new_path)
        rel_new = str(new_path.relative_to(root))
        rel_old = str(p.relative_to(root))
        mapping[rel_new] = rel_old
        print(f"  {rel_old}  ->  {rel_new}")

    map_path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"已改名 {len(mapping)} 个文件，映射写入 {map_path}")


def restore(root: Path) -> None:
    map_path = root / MAP_NAME
    if not map_path.exists():
        sys.exit(f"找不到 {MAP_NAME}，无法恢复。")

    mapping = json.loads(map_path.read_text(encoding="utf-8"))
    count = 0
    for rel_new, rel_old in mapping.items():
        cur = root / rel_new
        old = root / rel_old
        if not cur.exists():
            print(f"  跳过（不存在）: {rel_new}")
            continue
        cur.rename(old)
        print(f"  {rel_new}  ->  {rel_old}")
        count += 1

    map_path.unlink()
    print(f"已恢复 {count} 个文件，删除映射 {map_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="文件后缀名批量改 .json 再恢复")
    parser.add_argument("action", choices=["to-json", "restore"], help="动作")
    parser.add_argument("dir", help="目标文件夹")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="递归处理子目录（仅 to-json）"
    )
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.is_dir():
        sys.exit(f"不是文件夹: {root}")

    if args.action == "to-json":
        to_json(root, args.recursive)
    else:
        restore(root)


if __name__ == "__main__":
    main()
