"""Interactive command-line interface for the Everything search engine.

Usage:  python -m everything.cli [directories...]
"""

import os
import sys
import time

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from everything.everything import Everything, CATEGORIES, _CATEGORY_KEYS
else:
    from .everything import Everything, CATEGORIES, _CATEGORY_KEYS


def _detect_drives():
    drives = []
    for letter in 'ABCDEFGHIJ':
        p = f'{letter}:\\'
        if os.path.exists(p):
            drives.append(p)
    return drives


def run(directories=None):
    if directories is None:
        directories = _detect_drives()

    engine = Everything()

    print('Indexing, please wait...')
    start = time.perf_counter()
    for d in directories:
        if os.path.isdir(d):
            n, t = engine.index_directory(d)
            print(f'  {d}  ->  {n:,} files  ({t:.2f}s)')
    total_t = time.perf_counter() - start
    print(f'Total: {engine.total_files:,} files indexed in {total_t:.2f}s')
    print('Type a keyword to search, /quit to exit, /help for more\n')

    while True:
        try:
            raw = input('>> ').strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not raw:
            continue

        if raw == '/quit':
            break

        if raw == '/help':
            print('  keyword             — substring match (default)')
            print('  ^keyword            — prefix match (faster)')
            print('  keyword ext:py      — filter by extension')
            print('  keyword type:code   — filter by category (code/image/video/...)')
            print('  keyword type:folder — filter directories only')
            print('  *.py                — find all .py files (same as ext:py)')
            print('  /index <path>       — add a directory to the index')
            print('  /drives             — re-index all drives')
            print('  /types              — list all type categories')
            print('  /stats              — index statistics')
            print('  /quit               — exit')
            continue

        if raw.startswith('/index '):
            path = raw[7:].strip()
            if os.path.isdir(path):
                n, t = engine.index_directory(path)
                print(f'  {path}  ->  {n:,} files  ({t:.2f}s)')
            else:
                print(f'  Not a directory: {path}')
            continue

        if raw == '/drives':
            print('Re-indexing all drives...')
            engine.clear()
            total = engine.index_drives()
            print(f'Total: {total:,} files')
            continue

        if raw == '/types':
            for key, info in CATEGORIES.items():
                label = info['label']
                exts = ', '.join(sorted(info['exts']))
                print(f'  {label:14s}  ({key})  {exts}')
            continue

        if raw == '/stats':
            print(f'  Indexed: {engine.total_files:,} files')
            continue

        query = raw
        ext_filter = ''
        cat_filter = ''

        prefix_mode = False
        if query.startswith('^'):
            prefix_mode = True
            query = query[1:]

        import re
        m = re.search(r'\bext:(\w+)', query, re.IGNORECASE)
        if m:
            ext_filter = m.group(1)
            query = re.sub(r'\s*ext:\w+\s*', ' ', query).strip()

        m2 = re.search(r'\b(?:type|cat):(\w+)', query, re.IGNORECASE)
        if m2:
            cat_filter = m2.group(1)
            query = re.sub(r'\s*(?:type|cat):\w+\s*', ' ', query).strip()

        if not ext_filter and not cat_filter:
            m3 = re.match(r'^\*\.(\w+)$', query)
            if m3:
                ext_filter = m3.group(1)
                query = ''

        if not query and (ext_filter or cat_filter):
            query = ''

        if prefix_mode:
            results = engine.search_prefix(query)
        else:
            results = engine.search(query, ext=ext_filter, category=cat_filter)

        if not results:
            print('  (no results)')
        else:
            for p in results:
                print(f'  {p}')


if __name__ == '__main__':
    import sys
    dirs = sys.argv[1:] if len(sys.argv) > 1 else None
    run(dirs)
