import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .indexer import fast_scan, parallel_scan
from .trie import Trie

CATEGORIES = {
    'image':    {'label': '图片',          'exts': frozenset({'png','jpg','jpeg','gif','bmp','webp','svg','ico','tiff','tif','psd','raw','heic','avif'})},
    'video':    {'label': '视频',          'exts': frozenset({'mp4','avi','mkv','mov','wmv','flv','webm','m4v','mpg','mpeg','3gp','rmvb','ts'})},
    'audio':    {'label': '音频',          'exts': frozenset({'mp3','wav','flac','aac','ogg','wma','m4a','opus','ape','amr'})},
    'document': {'label': '文档',          'exts': frozenset({'pdf','doc','docx','txt','md','rtf','odt','log','wps','pages'})},
    'sheet':    {'label': '表格',          'exts': frozenset({'xls','xlsx','csv','tsv','ods','xlsm','numbers'})},
    'slides':   {'label': '演示文稿',      'exts': frozenset({'ppt','pptx','odp','key'})},
    'archive':  {'label': '压缩包',        'exts': frozenset({'zip','rar','7z','tar','gz','bz2','xz','iso','cab','arj'})},
    'code':     {'label': '代码',          'exts': frozenset({'py','js','ts','java','c','cpp','h','hpp','go','rs','sh','bat','ps1','rb','php','swift','kt','scala','r','m','mm','cs','fs','lua','pl','sql'})},
    'exe':      {'label': '可执行文件',    'exts': frozenset({'exe','dll','msi','bin','app','com','scr'})},
    'config':   {'label': '配置文件',      'exts': frozenset({'json','xml','yaml','yml','toml','ini','cfg','env','conf','properties'})},
    'font':     {'label': '字体',          'exts': frozenset({'ttf','otf','woff','woff2','eot'})},
    'ebook':    {'label': '电子书',        'exts': frozenset({'epub','mobi','azw3','djvu','fb2','cbz','cbr'})},
    'folder':   {'label': '文件夹',        'exts': frozenset()},
}

_CATEGORY_KEYS = frozenset(CATEGORIES.keys())
_CATEGORY_LABELS = [(c, info['label']) for c, info in CATEGORIES.items()]


def resolve_category(category: str) -> frozenset:
    c = category.lower().strip()
    return CATEGORIES[c]['exts'] if c in CATEGORIES else frozenset()


class Everything:

    __slots__ = ('_paths', '_normalized', '_extensions', '_is_dir',
                 '_trie', '_trie_built', '_watcher')

    def __init__(self):
        self._paths = []
        self._normalized = []
        self._extensions = []
        self._is_dir = []
        self._trie = None
        self._trie_built = False
        self._watcher = None

    # --- Indexing -----------------------------------------------------------

    def index_directory(self, root: str):
        root = os.path.abspath(root)
        start = time.perf_counter()
        is_drive = len(root) == 3 and root[1:] == ':\\'
        entries = parallel_scan(root) if is_drive else fast_scan(root)
        self._batch_add(entries)
        elapsed = time.perf_counter() - start
        return len(entries), elapsed

    def index_drives(self, drives=None):
        if drives is None:
            drives = [f'{l}:\\' for l in 'ABCDEFGHIJ' if os.path.exists(f'{l}:\\')]
        total = 0
        with ThreadPoolExecutor(max_workers=len(drives)) as pool:
            futures = {pool.submit(fast_scan, d): d for d in drives}
            for fut in as_completed(futures):
                entries = fut.result()
                self._batch_add(entries)
                total += len(entries)
        return total

    # --- Internal -----------------------------------------------------------

    def _batch_add(self, entries):
        if not entries:
            return
        paths = [e[0] for e in entries]
        self._paths.extend(paths)
        self._normalized.extend(p.lower() for p in paths)
        self._extensions.extend(_extract_ext(p) for p in paths)
        self._is_dir.extend(e[1] for e in entries)
        self._trie_built = False

    def _remove_path(self, path: str):
        key = path.lower()
        try:
            idx = self._normalized.index(key)
        except ValueError:
            return
        if self._trie_built:
            self._trie.remove(key, path)
        del self._paths[idx]
        del self._normalized[idx]
        del self._extensions[idx]
        del self._is_dir[idx]

    def _ensure_trie(self):
        if self._trie_built:
            return
        trie = Trie()
        insert = trie.insert
        for norm, path in zip(self._normalized, self._paths):
            insert(norm, path)
        self._trie = trie
        self._trie_built = True

    # --- Search -------------------------------------------------------------

    def search(self, query: str = '', ext: str = '', category: str = '',
               limit: int = 1000):
        if not query and not ext and not category:
            return []
        q = query.lower()
        e = ext.lstrip('.*').lower() if ext else ''
        is_folder = (category.lower().strip() == 'folder')
        cat_exts = resolve_category(category) if category and not is_folder else None
        results = []
        append = results.append
        for i, norm in enumerate(self._normalized):
            if q and q not in norm:
                continue
            if is_folder and not self._is_dir[i]:
                continue
            if not is_folder:
                file_ext = self._extensions[i]
                if e and file_ext != e:
                    continue
                if cat_exts is not None and file_ext not in cat_exts:
                    continue
            append(self._paths[i])
            if len(results) >= limit:
                break
        return results

    def search_prefix(self, prefix: str, limit: int = 1000):
        if not prefix:
            return []
        self._ensure_trie()
        return self._trie.search_prefix(prefix.lower(), limit)

    # --- Watching -----------------------------------------------------------

    def start_watching(self, directories):
        from .watcher import DirectoryWatcher
        self._watcher = DirectoryWatcher(
            on_added=self._add_one,
            on_removed=self._remove_path,
        )
        for d in directories:
            self._watcher.watch(d)
        self._watcher.start()

    def stop_watching(self):
        if self._watcher:
            self._watcher.stop()
            self._watcher = None

    def _add_one(self, path: str, is_dir: bool = False):
        key = path.lower()
        self._paths.append(path)
        self._normalized.append(key)
        self._extensions.append(_extract_ext(path) if not is_dir else '')
        self._is_dir.append(is_dir)
        if self._trie_built:
            self._trie.insert(key, path)

    # --- Stats --------------------------------------------------------------

    def clear(self):
        self._paths.clear()
        self._normalized.clear()
        self._extensions.clear()
        self._is_dir.clear()
        self._trie = None
        self._trie_built = False

    @property
    def total_files(self):
        return len(self._paths)


def _extract_ext(path: str) -> str:
    dot = path.rfind('.')
    if dot == -1:
        return ''
    sep = max(path.rfind('\\', 0, dot), path.rfind('/', 0, dot))
    if dot <= sep:
        return ''
    return path[dot + 1:].lower()
