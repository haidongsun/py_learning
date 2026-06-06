import argparse
import json
import os
import sys
import time
from collections import defaultdict

_SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for u in _SIZE_UNITS[1:]:
        n /= 1024.0
        if n < 1024:
            return f"{n:.1f} {u}"
    return f"{n:.1f} PB"


def _parse_exclude(raw: list) -> set:
    out = set()
    for p in raw:
        if p.startswith('*.'):
            out.add(('ext', p[1:]))
        else:
            out.add(('name', p))
    return out


def _is_excluded(name: str, exclude_set: set) -> bool:
    if ('name', name) in exclude_set:
        return True
    _, ext = os.path.splitext(name)
    if ext and ('ext', ext) in exclude_set:
        return True
    return False


def dir_total_size(dirpath: str, hidden: bool, exclude_set: set) -> int:
    """Fast recursive sum of all file sizes under a directory."""
    total = 0
    try:
        with os.scandir(dirpath) as it:
            for entry in it:
                name = entry.name
                if not hidden and name.startswith('.'):
                    continue
                if exclude_set and _is_excluded(name, exclude_set):
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        total += dir_total_size(entry.path, hidden, exclude_set)
                    elif entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    continue
    except OSError:
        pass
    return total


def scan_current(dirpath: str, hidden: bool, exclude_set: set, min_size: int):
    """Scan current directory — returns [(name, size, is_dir), ...]."""
    items = []
    try:
        with os.scandir(dirpath) as it:
            for entry in it:
                name = entry.name
                if not hidden and name.startswith('.'):
                    continue
                if exclude_set and _is_excluded(name, exclude_set):
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        sz = dir_total_size(entry.path, hidden, exclude_set)
                    elif entry.is_file(follow_symlinks=False):
                        sz = entry.stat(follow_symlinks=False).st_size
                    else:
                        continue
                except OSError:
                    continue
                if sz < min_size:
                    continue
                items.append((name, sz, entry.is_dir(follow_symlinks=False)))
    except OSError:
        pass
    return items


def walk_recursive(root: str, hidden: bool, exclude_set: set, min_size: int,
                   max_depth: int, root_files: list):
    """Recursive scan of subdirectories. Returns list of (fullpath, size, ext)."""
    files = list(root_files)
    root = os.path.abspath(root)
    root_file_names = {os.path.basename(f[0]) for f in root_files}
    stack = [(root, 0)]

    while stack:
        cur, depth = stack.pop()
        new_depth = 1 if depth == 0 else depth + 1
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    name = entry.name
                    if depth == 0 and name in root_file_names:
                        continue
                    if not hidden and name.startswith('.'):
                        continue
                    if exclude_set and _is_excluded(name, exclude_set):
                        continue
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    if is_dir:
                        if max_depth < 0 or depth < max_depth:
                            stack.append((entry.path, new_depth))
                    else:
                        try:
                            sz = entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            continue
                        if sz < min_size:
                            continue
                        files.append((entry.path, sz, os.path.splitext(name)[1].lower() or "(none)"))
        except OSError:
            continue

    return files


def print_items(items, root: str, recursive: bool = False):
    bar = "=" * 60
    tag = "[recursive]" if recursive else ""
    print(f"\n{bar}")
    print(f"  {root} {tag}")
    print(f"{bar}")
    if not items:
        print("  (empty)")
        return

    items_sorted = sorted(items, key=lambda x: x[1], reverse=True)
    max_name = min(max(len(str(i[0])) for i in items_sorted) + 4, 50)

    print(f"  {'Name':<{max_name}} {'Size':>10}  Type")
    print(f"  {'-'*(max_name + 20)}")
    for name, sz, is_dir in items_sorted:
        kind = "<DIR>" if is_dir else ""
        print(f"  {name:<{max_name}} {fmt_size(sz):>10}  {kind}")

    total = sum(sz for _, sz, _ in items_sorted)
    print(f"  {'-'*(max_name + 20)}")
    print(f"  {len(items_sorted)} item(s),  {fmt_size(total)}")


def main():
    parser = argparse.ArgumentParser(description="Fast file resource statistics")
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan (default: .)")
    parser.add_argument("-a", "--all", action="store_true", dest="hidden", help="Include hidden files")
    parser.add_argument("-e", "--exclude", nargs="*", default=[], metavar="P", help="Exclude patterns (e.g. '*.pyc')")
    parser.add_argument("-m", "--min-size", type=int, default=0, help="Min file size in bytes")
    parser.add_argument("-j", "--json", action="store_true", help="JSON output")
    parser.add_argument("-r", "--recursive", action="store_true", help="Show all files recursively (no dir rollup)")
    parser.add_argument("-d", "--max-depth", type=int, default=-1, help="Max depth for -r mode (-1=unlimited)")
    args = parser.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"'{args.path}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    exclude_set = _parse_exclude(args.exclude) if args.exclude else set()
    t0 = time.perf_counter()

    if args.recursive:
        cur_files = []
        for f, sz, _ in scan_current(root, args.hidden, exclude_set, args.min_size):
            cur_files.append((os.path.join(root, f), sz, os.path.splitext(f)[1].lower() or "(none)"))

        all_files = walk_recursive(root, args.hidden, exclude_set, args.min_size, args.max_depth, cur_files)
        items = [(os.path.relpath(f[0], root), f[1], False) for f in all_files]
        is_recursive = True
    else:
        items = scan_current(root, args.hidden, exclude_set, args.min_size)
        is_recursive = False

    t1 = time.perf_counter()

    if args.json:
        output = {
            "path": root,
            "elapsed_ms": round((t1 - t0) * 1000, 2),
            "items": [
                {"name": str(n), "size": sz, "size_human": fmt_size(sz), "is_dir": d}
                for n, sz, d in sorted(items, key=lambda x: x[1], reverse=True)
            ]
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print_items(items, root, recursive=is_recursive)
    print(f"\n  Done in {((t1 - t0) * 1000):.1f} ms\n")


if __name__ == "__main__":
    main()
