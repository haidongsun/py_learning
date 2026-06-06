import os
from concurrent.futures import ThreadPoolExecutor, as_completed

EXCLUDED_DIRS = frozenset({
    '$Recycle.Bin', 'System Volume Information', 'Windows', 'WinSxS',
    'node_modules', '__pycache__', '.git', '.svn', '.hg',
})

_EXCLUDED_PREFIXES = ('.',)


def fast_scan(root_path):
    """Iterative scanner — returns list of (path, is_dir) tuples."""
    entries = []
    stack = [root_path]
    append = entries.append
    push = stack.append
    pop = stack.pop
    scandir = os.scandir

    while stack:
        dirpath = pop()
        try:
            with scandir(dirpath) as scan:
                for entry in scan:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            name = entry.name
                            if name in EXCLUDED_DIRS or name.startswith(_EXCLUDED_PREFIXES):
                                continue
                            path = entry.path
                            append((path, True))
                            push(path)
                        else:
                            append((entry.path, False))
                    except OSError:
                        continue
        except OSError:
            pass

    return entries


def parallel_scan(root_path, max_workers=8):
    """Scan top-level directories in parallel; merges (path, is_dir) tuples."""
    top_dirs = []
    top_entries = []
    scandir = os.scandir
    try:
        with scandir(root_path) as scan:
            for entry in scan:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        name = entry.name
                        if name not in EXCLUDED_DIRS and not name.startswith(_EXCLUDED_PREFIXES):
                            top_dirs.append(entry.path)
                    else:
                        top_entries.append((entry.path, False))
                except OSError:
                    continue
    except OSError:
        pass

    if not top_dirs:
        return top_entries

    workers = min(max_workers, len(top_dirs))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fast_scan, d): d for d in top_dirs}
        for fut in as_completed(futures):
            top_entries.extend(fut.result())

    return top_entries
