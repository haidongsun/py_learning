import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for u in _UNITS[1:]:
        n /= 1024.0
        if n < 1024:
            return f"{n:.1f} {u}"
    return f"{n:.1f} PB"


def _parse_exclude(raw):
    names = set()
    exts = set()
    for p in raw:
        if p.startswith('*.'):
            exts.add(p[1:])
        else:
            names.add(p)
    return names, exts


def _should_skip(name, hidden, names_set, exts_set):
    if not hidden and name and name[0] == '.':
        return True
    if names_set and name in names_set:
        return True
    if exts_set:
        _, ext = os.path.splitext(name)
        if ext in exts_set:
            return True
    return False


def _dir_size(dirpath, hidden, names_set, exts_set):
    """Recursive sum of all file sizes under dirpath."""
    total = 0
    try:
        with os.scandir(dirpath) as it:
            for entry in it:
                if _should_skip(entry.name, hidden, names_set, exts_set):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    total += _dir_size(entry.path, hidden, names_set, exts_set)
                elif entry.is_file(follow_symlinks=False):
                    try:
                        total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
    except OSError:
        pass
    return total


def scan(root, hidden, names_set, exts_set, min_size, parallel=True):
    items = []
    dir_tasks = []

    try:
        with os.scandir(root) as it:
            for entry in it:
                if _should_skip(entry.name, hidden, names_set, exts_set):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    dir_tasks.append((entry.path, entry.name))
                elif entry.is_file(follow_symlinks=False):
                    try:
                        sz = entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
                    if sz >= min_size:
                        items.append((entry.name, sz, False))
    except OSError:
        pass

    if dir_tasks:
        if parallel and len(dir_tasks) > 1:
            with ThreadPoolExecutor(max_workers=min(len(dir_tasks), (os.cpu_count() or 4))) as pool:
                futures = {
                    pool.submit(_dir_size, d[0], hidden, names_set, exts_set): d
                    for d in dir_tasks
                }
                for fut in as_completed(futures):
                    name = futures[fut][1]
                    sz = fut.result()
                    if sz >= min_size:
                        items.append((name, sz, True))
        else:
            for dpath, name in dir_tasks:
                sz = _dir_size(dpath, hidden, names_set, exts_set)
                if sz >= min_size:
                    items.append((name, sz, True))

    items.sort(key=lambda x: x[1], reverse=True)
    return items


def print_items(items, root):
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  {root}")
    print(f"{bar}")
    if not items:
        print("  (empty)")
        return

    name_w = min(max(len(n) for n, _, _ in items) + 4, 50)
    print(f"  {'Name':<{name_w}} {'Size':>10}  Type")
    print(f"  {'-' * (name_w + 20)}")
    for name, sz, is_dir in items:
        print(f"  {name:<{name_w}} {fmt_size(sz):>10}  {'<DIR>' if is_dir else ''}")

    total = sum(sz for _, sz, _ in items)
    print(f"  {'-' * (name_w + 20)}")
    print(f"  {len(items)} item(s),  {fmt_size(total)}")


def main():
    parser = argparse.ArgumentParser(description="Fast file resource statistics")
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan (default: .)")
    parser.add_argument("-a", "--all", action="store_true", dest="hidden", help="Include hidden files")
    parser.add_argument("-e", "--exclude", nargs="*", default=[], metavar="P",
                        help="Exclude patterns (e.g. '*.pyc' 'node_modules')")
    parser.add_argument("-m", "--min-size", type=int, default=0, help="Min file size in bytes")
    parser.add_argument("-j", "--json", action="store_true", help="JSON output")
    parser.add_argument("-p", "--parallel", action="store_true", help="Enable parallel dir scanning (for large trees)")
    args = parser.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"'{args.path}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    names_set, exts_set = _parse_exclude(args.exclude)
    t0 = time.perf_counter()

    items = scan(root, args.hidden, names_set, exts_set, args.min_size,
                 parallel=args.parallel)

    t1 = time.perf_counter()

    if args.json:
        print(json.dumps({
            "path": root,
            "elapsed_ms": round((t1 - t0) * 1000, 2),
            "items": [{"name": n, "size": sz, "size_human": fmt_size(sz), "is_dir": d}
                      for n, sz, d in items]
        }, indent=2, ensure_ascii=False))
        return

    print_items(items, root)
    print(f"\n  Done in {((t1 - t0) * 1000):.1f} ms\n")


if __name__ == "__main__":
    main()
