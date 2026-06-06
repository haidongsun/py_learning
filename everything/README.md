# Everything 实现原理 & Python 复刻

## 1. Everything 是什么

[Everything](https://www.voidtools.com/) 是 Windows 上一款极快的文件名搜索引擎。用户输入关键词的瞬间即返回匹配结果——这个速度远超 Windows 自带的文件搜索（后者需要递归遍历目录树）。

## 2. 核心原理

Everything 的极速搜索建立在三个关键技术之上：

### 2.1 NTFS MFT（主文件表）直接读取

```
┌──────────────────────────────────────────────┐
│                  NTFS 卷                      │
│  ┌───────┐  ┌───────┐  ┌───────┐            │
│  │ $Boot │  │ $MFT  │  │ $Log  │  ...       │
│  └───────┘  └───┬───┘  └───────┘            │
│                 │                             │
│    ┌────────────┼────────────┐               │
│    ▼            ▼            ▼               │
│  ┌─────┐    ┌─────┐    ┌─────┐              │
│  │记录1│    │记录2│    │记录N│   ← 每个文件   │
│  │文件名│    │文件名│    │文件名│     一条记录   │
│  │属性  │    │属性  │    │属性  │              │
│  │时间戳│    │时间戳│    │时间戳│              │
│  └─────┘    └─────┘    └─────┘              │
└──────────────────────────────────────────────┘
```

- NTFS 卷的所有文件元数据集中存储在一个名为 `$MFT` 的特殊文件中
- 每个文件和目录对应 `$MFT` 中的一条固定大小记录（通常 1KB）
- `$MFT` 本身是一个 B-tree 结构，支持高效的范围查询
- **Everything 直接解析 `$MFT` 原始数据**，绕过了 Win32 API `FindFirstFile`/`FindNextFile` 的递归目录遍历

```
传统搜索：
  C:\ → dir → subdir1 → subdir2 → ... → fileX      O(目录深度 × 文件数)

Everything：
  \\.\C: → 读取 $MFT 记录 → 直接获取全量文件名      O(文件总数)
```

`$MFT` 按线性顺序存储记录，Everything 只需要一次顺序扫描就能获取整个卷的文件列表，比递归遍历目录树快 1-2 个数量级。

### 2.2 USN Journal（变更日志）增量更新

```
时间线 ──────────────────────────────────────────────►

文件操作:    创建A    修改B    删除C    重命名D

USN Journal:  [rec#1] [rec#2] [rec#3] [rec#4]  ← 追加写入
               ↑
          USN (Update Sequence Number) 单调递增

Everything:
  启动时:  记录当前 USN
  运行时:  定期查询 "USN > 上次记录值" 的变更
           → 增量更新内存索引（无需重新扫描全盘）
```

- NTFS 维护一个 USN Change Journal，记录所有文件变更
- 每条记录包含：USN（序号）、文件名、文件引用号、变更类型
- Everything 仅查询自上次检查以来新增的变更记录，实现 O(变更量) 的增量更新

### 2.3 全内存索引 + 高效数据结构

```
         ┌──────────────────────────┐
         │      内存中的索引         │
         │                          │
         │  ┌────────────────────┐  │
         │  │  文件名 → 路径映射  │  │
         │  │  (大小写归一化)     │  │
         │  └────────────────────┘  │
         │                          │
         │  ┌────────────────────┐  │
         │  │  Trie / 后缀数组    │  │
         │  │  (用于子串匹配)     │  │
         │  └────────────────────┘  │
         │                          │
         │  ┌────────────────────┐  │
         │  │  NTFS 文件引用号    │  │
         │  │  → 文件路径缓存     │  │
         │  └────────────────────┘  │
         └──────────────────────────┘
```

- 整个文件名数据库加载到内存中（百万级文件约 100-200MB）
- 使用紧凑的 Trie 数据结构，支持 O(k) 的前缀查找（k = 查询字符串长度）
- **大小写归一化**：存储时统一转小写，搜索时同样归一化
- **文件引用号**（File Reference Number）作为主键，解决文件重命名时的索引更新

## 3. Python 复刻架构

```
┌──────────┐  ┌──────────┐
│  gui.py  │  │  cli.py  │   用户界面层
└────┬─────┘  └────┬─────┘
     └──────┬──────┘
            ▼
   ┌─────────────────┐
   │  everything.py  │       搜索引擎核心
   │  ┌─────────────┐│
   │  │ _paths       ││      原始路径列表
   │  │ _normalized  ││      归一化小写路径
   │  │ _extensions  ││      预提取的扩展名
   │  │ _trie (lazy) ││      延迟构建的 Trie
   │  └─────────────┘│
   └───┬───────┬─────┘
       │       │
       ▼       ▼
  ┌────────┐ ┌──────────┐
  │indexer │ │ watcher  │    数据采集层
  │.py     │ │ .py      │
  │fast_sca│ │ReadDir   │
  │n()     │ │ChangesW  │
  │parallel│ │          │
  │_scan() │ │          │
  └────────┘ └──────────┘
```

### 模块职责

| 文件 | 职责 |
|------|------|
| `trie.py` | 紧凑前缀树，`__slots__` 优化，支持前缀收集和删除 |
| `indexer.py` | 迭代栈式 `os.scandir()` 扫描器 + 顶层目录并行扫描 |
| `watcher.py` | Win32 `ReadDirectoryChangesW` 文件变更监控（ctypes） |
| `everything.py` | 搜索引擎核心：批量索引、延迟 Trie、子串/前缀/扩展名过滤 |
| `cli.py` | 交互式命令行，支持 `ext:` 和 `*.ext` 过滤语法 |
| `gui.py` | Tkinter GUI，实时搜索 + 文件类型下拉筛选 |

### 与原始 Everything 的差异

| 维度 | 原始 Everything | Python 复刻 |
|:---|:---|:---|
| 文件发现 | NTFS `$MFT` 直接解析 | `os.scandir()` 迭代遍历 |
| 更新机制 | USN Journal 增量查询 | `ReadDirectoryChangesW` API |
| 子串搜索 | 高度优化的 C++ Trie/Suffix Array | 线性扫描 + 延迟构建 Trie |
| 内存开销 | ~100MB（千万级文件） | ~200MB（百万级文件） |
| 权限要求 | 无需管理员 | 无需管理员 |

## 4. 性能优化

### 4.1 迭代栈替代递归（indexer.py）

**问题**：递归 `yield from` 每个目录触发一次 Python 函数调用，深度嵌套导致大量 C/Python 边界切换。

**方案**：显式栈 + `os.scandir()` 迭代遍历：

```python
def fast_scan(root_path):
    paths = []
    stack = [root_path]
    append = paths.append
    push = stack.append
    pop = stack.pop

    while stack:
        dirpath = pop()
        with scandir(dirpath) as entries:
            for entry in entries:
                if entry.is_dir(...):
                    push(entry.path)
                else:
                    append(entry.path)      # 直接追加，无 yield 开销
    return paths                            # 返回列表，无生成器开销
```

- 局部变量绑定（`append` / `push` / `pop` / `scandir`）避免全局查找
- `frozenset` 替代 `set` 加速排除目录判重

### 4.2 Trie 延迟构建（everything.py）

**问题**：索引时逐条插入 Trie —— 734K 文件 × 平均 80 字符/路径 = **~59M 次字典操作**，占索引耗时 70%+。

**方案**：索引阶段完全不碰 Trie，仅在首次 `search_prefix()` 调用时构建：

```python
# 索引时：纯列表追加
def _batch_add(self, paths):
    self._paths.extend(paths)
    self._normalized.extend(p.lower() for p in paths)
    self._extensions.extend(self._exts(paths))
    self._trie_built = False           # 标记失效

# 首次前缀搜索时才构建
def _ensure_trie(self):
    if self._trie_built:
        return
    trie = Trie()
    for norm, path in zip(self._normalized, self._paths):
        trie.insert(norm, path)
    self._trie = trie
    self._trie_built = True
```

搜索默认使用 `search()`（线性遍历 `_normalized` + `_extensions` 列表），不依赖 Trie。

### 4.3 二层并行扫描（indexer.py）

```
第一层 — 盘符级并行：
  C:\ ──── Thread-1
  D:\ ──── Thread-2  ─── 同时扫描，I/O 并行
  E:\ ──── Thread-3

第二层 — 磁盘内顶层目录并行：
  D:\
  ├─ \data      ─── Thread-1
  ├─ \workspace ─── Thread-2
  ├─ \backup    ─── Thread-3   ─── 各子线程调用 fast_scan()
  └─ \media     ─── Thread-4
```

- `parallel_scan(root)`：提取盘符根下顶层目录，每个子目录提交到 `ThreadPoolExecutor` 独立扫描
- `index_drives(drives)`：每个盘符提交为独立 future，`as_completed` 逐批合并结果
- `os.scandir` 在 I/O 时释放 GIL，多线程可有效并行

### 4.4 批量追加 + 预提取扩展名

```python
# 优化前：逐条方法调用（每文件 1 次 _add_path → 3 次 append + 1 次 trie 插入）
for path in scan_directory(root):
    self._add_path(path)

# 优化后：批量 extend，扩展名一次提取
paths = fast_scan(root)
self._paths.extend(paths)
self._normalized.extend(p.lower() for p in paths)
self._extensions.extend(_extract_ext(p) for p in paths)
```

- `list.extend()` 在 C 层面批量扩容，减少 realloc
- 扩展名用 `rfind('.')` + 路径分隔符判断，避免 `os.path.splitext` 的 tuple 拆包开销

### 4.5 优化效果量化

| 阶段 | 操作 | 734K 文件耗时 | 吞吐 |
|------|------|:---:|:---:|
| 初版 | 递归 + 逐条 Trie 插入 | ~30s | ~24K/s |
| 删 Trie + 迭代栈 | `fast_scan` + `_batch_add` | ~8s | ~92K/s |
| + 二层并行 | `parallel_scan` + 盘符并行 | **5.86s** | **125K/s** |

测试环境：Windows 10, SSD, Python 3.10, C:\Users (277K) + D:\ (457K)。

## 5. 搜索过程

```
用户输入 "cli ext:py"
            │
            ▼
    解析: query="cli", ext="py"
            │
            ▼
    遍历 _normalized[i] 和 _extensions[i]
            │
            ├─ "cli" in _normalized[i] ?   (子串匹配)
            ├─ _extensions[i] == "py" ?    (扩展名匹配)
            └─ 命中 → 追加 _paths[i]
            │
            ▼
    返回结果:
      D:\...\everything\cli.py
      D:\...\chatbot\backend\mcp_client.py
```

- **子串匹配**：在线性 `_normalized` 列表中做 `query in path` 检查，O(n) 但常数极小
- **扩展名过滤**：与子串匹配同步进行，不额外遍历
- **前缀匹配**：调用 `_ensure_trie()` 构建 Trie 后 O(k) 查找

## 6. 使用方式

### 命令行

```bash
python -m everything.cli                    # 默认扫描所有盘符
python -m everything.cli D:\ E:\            # 指定目录/盘符

>> readme ext:md                             # 关键词 + 扩展名过滤
>> *.py                                      # 等价于 ext:py
>> ^D:\workspace                             # 前缀匹配（更快）
>> /index C:\Users                           # 运行时追加索引
>> /drives                                   # 重新扫描所有盘符
>> /stats                                    # 索引统计
>> /quit                                     # 退出
```

### GUI

```bash
python -m everything.gui
```

- 搜索栏实时输入实时结果
- 右侧 **Type** 下拉框支持按扩展名筛选（py / md / xlsx / pdf / ...）
- 双击结果打开所在文件夹

### 编程调用

```python
from everything import Everything

engine = Everything()

# 扫描单个目录或盘符（盘符自动并行顶层目录）
engine.index_directory('D:\\')
engine.index_directory('C:\\Users\\Administrator')

# 并行扫描多个盘符
engine.index_drives(['C:\\', 'D:\\'])

# 搜索
results = engine.search('python')                    # 子串匹配
results = engine.search('game', ext='py')            # 子串 + 扩展名
results = engine.search_prefix('D:\\document')       # 前缀匹配

# 实时监控
engine.start_watching(['D:\\workspace'])

print(f'Total: {engine.total_files:,} files')
```

## 7. 与 Everything 的关键代码对比

### Trie 前缀树（trie.py）

```python
trie.insert('d:\\doc\\readme.txt', 'D:\\Doc\\README.txt')
# → 内部 key 归一化为小写，value 保留原始大小写

trie.search_prefix('d:\\doc')   # → ['D:\\Doc\\README.txt', ...]
# → O(k) 遍历到目标节点，然后 DFS 收集所有值
```

### ReadDirectoryChangesW 文件监控（watcher.py）

通过 `ctypes` 调用 Windows 内核 API：

```python
handle = CreateFileW(path, FILE_LIST_DIRECTORY, ...)
ReadDirectoryChangesW(handle, buf, buf_size, True,
    FILE_ACTION_ADDED | FILE_ACTION_REMOVED | ...)
# → 阻塞等待，目录变更时返回 FILE_NOTIFY_INFORMATION 结构列表
# → 回调 engine._add_one() / engine._remove_path() 增量更新索引
```

### 快速扩展名提取（everything.py）

```python
def _extract_ext(path):
    dot = path.rfind('.')
    if dot == -1:
        return ''
    sep = max(path.rfind('\\', 0, dot), path.rfind('/', 0, dot))
    if dot <= sep:
        return ''
    return path[dot + 1:].lower()
```

仅用 `rfind` 两次，比 `os.path.splitext` 的 tuple 拆包更轻量。
