# File Stats — 设计文档

## 1. 概述

File Stats 是一个极速文件资源统计工具，提供 CLI 和 GUI 两种形态。核心能力：扫描指定目录，按体积降序展示所有条目（文件显示自身大小，文件夹显示递归总大小），支持层级钻取、缓存复用、右键文件操作。

- **语言**：Python 3.10+
- **依赖**：零外部依赖（标准库 only）
- **平台**：Windows / macOS / Linux（仅右键 Open 功能依赖 Windows API）

## 2. 项目结构

```
file_stats/
├── main.py      # CLI 命令行工具（165 行）
├── gui.py       # Tkinter 桌面 GUI（421 行）
└── DESIGN.md    # 本文档
```

## 3. 模块设计

### 3.1 CLI (`main.py`)

**入口**：`python file_stats/main.py [path] [options]`

**参数**：

| 参数 | 说明 |
|------|------|
| `path` | 目标目录，默认 `.` |
| `-a, --all` | 包含隐藏文件 |
| `-e, --exclude` | 排除模式（如 `*.pyc node_modules`） |
| `-m, --min-size` | 最小文件体积过滤（字节） |
| `-j, --json` | JSON 输出 |
| `-p, --parallel` | 启用多线程并行扫描子目录 |

**核心流程**：

```
main() → _parse_exclude() → scan() → print_items() / JSON
```

- `_parse_exclude()`：将排除模式分离为名称集合 + 扩展名集合，O(1) 匹配
- `scan()`：`os.scandir()` 扫当前目录 → 对子目录递归 `_dir_size()` 求总大小 → 按体积降序排列
- `print_items()`：格式化为表格输出

### 3.2 GUI (`gui.py`)

**入口**：`python file_stats/gui.py [start_dir]`

**UI 布局**：

```
┌─────────────────────────────────────────────┐
│ Path: [________________________________] [Browse] [Go] │
│ [↑ Up] [↻ Refresh] [⌂ Root]         [x] Parallel      │
│ /home/user/projects                                    │
├──────────┬───────┬───────┬──────────┬──────────┬───────┤
│ Name     │ Size  │ Files │ Share    │ Modified │ Type  │
├──────────┼───────┼───────┼──────────┼──────────┼───────┤
│ chatbot  │73.0KB │   12  │ ████ 25% │2026-06-06│  📁   │
│ main.py  │ 223 B │    1  │ █ 0.1%   │2026-06-05│  📄   │
└──────────┴───────┴───────┴──────────┴──────────┴───────┘
│  11 items  │  152 files  │  287.8 KB  │  0.7 ms         │
└─────────────────────────────────────────────────────────┘
```

**类结构**：

```
FileStatsApp
├── _build_ui()        # 构建 Tkinter 界面
├── _navigate(path)    # 目录导航（核心入口）
├── _populate()        # 填充 Treeview 数据
├── _sort(col)         # 列排序
├── _on_double_click() # 双击钻入子目录
├── _on_right_click()  # 右键菜单
├── _delete_item()     # 删除文件/目录
├── _copy_to_clipboard()
├── _scan_done()       # 后台扫描完成回调
└── _set_buttons_state() # 按钮启用/禁用
```

## 4. 数据结构

### 4.1 条目元组

GUI 中每个条目为 5 元组：

```python
(name: str, size: int, is_dir: bool, file_count: int, mtime: float)
```

CLI 中为 3 元组（不含 file_count 和 mtime）。

### 4.2 缓存结构

```python
_cache: dict[str, tuple[list, int]]
# key   = 目录绝对路径
# value = (items: list[5-tuple], total_files: int)
```

- `items`：该目录下所有条目的 5 元组列表，已按 size 降序排序
- `total_files`：该目录递归包含的文件总数

### 4.3 扫描返回值

```python
_dir_size_with_cache() → (total_size, file_count, dir_mtime)
scan_flat()            → (items, total_file_count)
```

## 5. 核心算法

### 5.1 递归目录大小计算（带缓存）

```
_dir_size_with_cache(dirpath, cache):
    total = 0, file_count = 0, items = []
    for entry in scandir(dirpath):
        if hidden/excluded: skip
        if is_dir:
            sub_total, sub_count = _dir_size_with_cache(entry.path, cache)
            total += sub_total; file_count += sub_count
            items.append((name, sub_total, True, sub_count, mtime))
        if is_file:
            total += st_size; file_count += 1
            items.append((name, st_size, False, 1, mtime))
    items.sort(key=size, reverse=True)
    cache[dirpath] = (items, file_count)
    return (total, file_count, os.stat(dirpath).st_mtime)
```

- 每个目录仅访问一次，结果存入全局缓存
- 首次扫描后，所有已访问子目录的条目列表已就绪
- 命中缓存的导航零 I/O，状态栏显示 `(cached)`

### 5.2 并行扫描

```
scan_flat(dirpath, cache, parallel=True):
    # 当前目录文件：直接 os.scandir() 获取
    # 子目录：提交到 ThreadPoolExecutor
    futures = {pool.submit(_dir_size_with_cache, d, cache): d for d in dir_tasks}
    for fut in as_completed(futures):
        sz, fc, mt = fut.result()
        items.append(...)
```

- 线程数 = `min(len(subdirs), cpu_count())`
- `os.scandir()` 在 I/O 等待期间释放 GIL，线程真实并行

## 6. 性能设计

### 6.1 关键技术选型

| 决策 | 理由 |
|------|------|
| `os.scandir()` 替代 `os.walk()` | Windows 上 `DirEntry.stat()` 已缓存，免去额外 syscall |
| 元组替代 dataclass | 热路径零对象分配开销 |
| 排除匹配用 `set` | O(1) 查找 vs O(n) 列表遍历 |
| 默认串行 | 小目录无线程池创建开销（~0.7ms vs ~2ms） |
| GUI 后台线程 | `threading.Thread` + `root.after()` 保持 UI 响应 |
| 扫描时禁用按钮 | `_scanning` 标志位 + 遍历禁用 ttk 控件 |

### 6.2 实测数据

测试目录：`py_learning` 项目根（含 `node_modules` 117MB）

| 模式 | 耗时 | 说明 |
|------|------|------|
| CLI 串行 | ~6ms | 仅算大小，无缓存 |
| GUI 带缓存 | ~7ms | +1ms 换取 136 个目录预缓存 |
| GUI 缓存命中 | <0.1ms | 无磁盘 I/O |

## 7. 交互设计

### 7.1 导航

| 操作 | 触发方式 |
|------|---------|
| 钻入子目录 | 双击行 / Enter |
| 返回上级 | `↑ Up` 按钮 / Backspace |
| 跳转根目录 | `⌂ Root` 按钮 |
| 刷新 | `↻ Refresh` 按钮 |
| 浏览选择 | `Browse...` 按钮 / 路径栏 Enter |

### 7.2 右键菜单

| 菜单项 | 功能 |
|--------|------|
| Open | `os.startfile()` 调用关联程序打开 |
| Open in Explorer | `explorer /select,` 定位文件 |
| Copy Path | 复制完整路径到剪贴板 |
| Delete | 确认后 `shutil.rmtree` / `os.remove` 永久删除 |
| Open Current Folder | 打开当前浏览目录 |
| Copy Current Folder Path | 复制当前目录路径 |

### 7.3 排序

点击任意列标题切换排序（Name / Size / Files / Modified），默认 Size 降序。

### 7.4 Share 列

```
████████████ 50.2%    # 每 5% 一个 █，最多 10 个字符
███ 15.8%
```

## 8. 健壮性

- 扫描期间所有按钮禁用 + 操作拦截（`_scanning` 标志位）
- 权限错误 / 不存在的路径 → `OSError` 静默跳过
- 删除确认对话框 + 异常捕获
- 路径规范化：`os.path.abspath(os.path.expanduser())`
- 隐藏文件跳过：判断首字符 `.`（不含 `.git` 等名称匹配的场景可用 `-e` 排除）

## 9. CLI vs GUI 对照

| 特性 | CLI | GUI |
|------|-----|-----|
| 当前目录展示 | ✓ | ✓ |
| 文件夹递归总大小 | ✓ | ✓ |
| 文件数统计 | ✗ | ✓ |
| 占比进度条 | ✗ | ✓ |
| 修改时间 | ✗ | ✓ |
| 层级钻取 | ✗ | ✓（双击） |
| 扫描缓存 | ✗ | ✓ |
| 右键文件操作 | ✗ | ✓ |
| JSON 输出 | ✓ | ✗ |
| 排除模式 | ✓ | ✗（自动跳过隐藏文件） |
| 并行扫描 | ✓（-p）| ✓（勾选） |
