# Calculator — 项目设计文档

## 1. 项目概述

一款基于 Python Tkinter 的桌面科学计算器，支持基础四则运算、科学函数、历史记录、键盘输入和亮/暗主题切换。

| 属性 | 值 |
|---|---|
| 语言 | Python 3.10+ |
| GUI 框架 | Tkinter（内置，零依赖） |
| 额外依赖 | 无 |
| 运行方式 | `python -m calculator.app` |
| 代码量 | ~550 行（10 个源文件） |

---

## 2. 架构设计

采用**三层简单分层架构**：

```
┌─────────────────────────────────────────────────────┐
│                    app.py (入口层)                    │
│                  创建 Tk 根窗口，启动主循环               │
├─────────────────────────────────────────────────────┤
│                  gui/ (交互层)                        │
│   main_window.py  ←── 总控制器，编排所有 GUI 组件        │
│   display.py      ←── 显示屏（表达式行 + 结果行）         │
│   button_grid.py  ←── 按钮网格 + 主题配色               │
│   history_panel.py←── 历史记录侧栏                     │
│   theme_manager.py←── 主题状态 + 观察者通知              │
├─────────────────────────────────────────────────────┤
│                  core/ (核心层)                       │
│   calculator.py   ←── 安全表达式求值引擎                 │
│   history.py      ←── 历史记录持久化存储                 │
└─────────────────────────────────────────────────────┘
```

**依赖方向**：`app → gui → core`，`core` 不依赖 `gui`，`gui` 之间通过 `main_window` 协调。

---

## 3. 模块详细设计

### 3.1 `calculator/app.py` — 入口

```
main()
  → tk.Tk()                      创建根窗口
  → CalculatorApp(root)          注入根窗口，触发全部初始化
  → root.mainloop()              进入事件循环
```

不包含任何业务逻辑，仅负责启动。

### 3.2 `core/calculator.py` — 计算引擎

**函数**：`safe_eval(expression: str) -> str`

**安全策略**：

1. 用 `compile(expr, '<calc>', 'eval')` 编译表达式为字节码
2. 遍历 `code.co_names`，确保每个名称在白名单 `namespace` 中
3. `eval(code, {'__builtins__': {}}, namespace)` 在无内置函数的沙箱中执行
4. 捕获所有异常，返回友好的错误字符串

**白名单函数**：

| 名称 | 映射 | 说明 |
|---|---|---|
| `sin`, `cos`, `tan` | `math.sin/cos/tan` | 三角函数 |
| `log` | `math.log10` | 以 10 为底的对数 |
| `ln` | `math.log` | 自然对数 (e 为底) |
| `sqrt` | `math.sqrt` | 平方根 |
| `pow` | `math.pow` | 幂运算 |
| `pi`, `e` | `math.pi`, `math.e` | 数学常数 |
| `factorial` | `math.factorial` | 阶乘 |
| `abs` | `abs` | 绝对值 |
| `radians`, `degrees` | `math.radians/degrees` | 角度/弧度转换 |

**结果格式化**：
- 浮点数：`.12f` 精度 + 去尾零 → 最大 12 位有效数字
- 近零值 `< 1e-12` → 归零，避免 `-0.0` 或 `1e-15` 等显示
- 无穷、NaN → 对应错误提示

**错误处理层次**：

```
try:
    compile → validate names → eval → format
except ZeroDivisionError     → "Error: Division by zero"
except SyntaxError/NameError → "Error: Invalid Expression"
except OverflowError          → "Error: Overflow"
except Exception              → "Error"
```

### 3.3 `core/history.py` — 历史记录

**数据结构**：

```
HistoryEntry (dataclass)
├── expression: str      # 原始表达式，如 "3*5+sin(45)"
├── result: str          # 计算结果，如 "13.535533905932"
└── timestamp: str       # 创建时间戳，格式 "YYYY-MM-DD HH:MM:SS"
```

**HistoryStore 类**：

| 方法 | 说明 |
|---|---|
| `__init__(max=100)` | 初始化，自动从 `calculator/history.json` 加载 |
| `add(expr, result)` | 头部插入新记录，超过上限截断，自动保存 |
| `clear()` | 清空内存 + 删除文件内容 |
| `entries` (property) | 返回记录的浅拷贝列表（防止外部修改） |

**持久化**：JSON 文件 `calculator/history.json`，写入失败静默忽略（避免阻塞 UI）。

### 3.4 `gui/theme_manager.py` — 主题管理

**设计模式**：观察者模式（订阅/通知）

```
ThemeManager
├── _current: Dict     ← 当前主题色板 (LIGHT_THEME 或 DARK_THEME)
├── _is_dark: bool     ← 当前是否为暗色模式
├── _listeners: List   ← 主题变更回调列表
├── toggle()           → 切换亮/暗，触发 _notify()
└── subscribe(cb)      → 注册回调，主题变更时自动调用 cb(theme_dict)
```

**主题色板结构**（每个主题 18 个色值）：

| 键 | 说明 | 示例(暗色) |
|---|---|---|
| `bg` | 窗口背景 | `#1C1C1E` |
| `display_bg/fg` | 显示屏背景/前景 | `#2C2C2E` / `#FFF` |
| `number_bg/fg` | 数字按钮 | `#3A3A3C` / `#FFF` |
| `operator_bg/fg` | 运算符按钮 `+ − × ÷` | `#FF9500` / `#FFF` |
| `equal_bg/fg` | 等号按钮 | `#0A84FF` / `#FFF` |
| `clear_bg/fg` | 清除按钮 `C CA ⌫` | `#D63031` / `#FFF` |
| `sci_bg/fg` | 科学函数按钮 | `#505050` / `#FFF` |
| `paren_bg/fg` | 括号按钮 | `#505050` / `#FFF` |
| `*_active_bg` | 各分类按钮的 hover 颜色 | 比 bg 亮 15%~20% |

### 3.5 `gui/display.py` — 显示屏

继承 `ttk.Frame`，双行显示：

```
┌──────────────────────────────┐
│  3*5+sin(45)           ← 表达式行 (Consolas 13pt, 灰色)  │
│         13.535533905932 ← 结果行 (Consolas 28pt bold, 黑/白) │
└──────────────────────────────┘
```

| 方法 | 说明 |
|---|---|
| `set_expression(text)` | 设置表达式行内容（`StringVar`） |
| `set_result(text)` | 设置结果行内容，初始值 `'0'` |
| `_apply_theme(theme)` | 根据主题更新背景色和前景色 |

### 3.6 `gui/button_grid.py` — 按钮网格

**按钮布局**（5 列 × 9 行，末尾 `=` 跨 2 行）：

```
C    CA   ⌫    ÷    %
7    8    9    ×   sin
4    5    6    −   cos
1    2    3    +   tan
±    0    .    (    )
π    e    x²   √    ┐
xⁿ  ¹/x   n!   ln   ┘ = (rowspan=2)
```

**数据定义**：

```python
BUTTON_ROWS = [
    [('C', 'clear', 1), ('CA', 'clear', 1), ...],  # 每行: [(文本, 分类, rowspan), ...]
    ...
]
```

**按钮分类 → 配色映射**：

```
分类 'number'    → number_bg / number_fg / number_active_bg
分类 'operator'  → operator_bg / operator_fg / operator_active_bg
分类 'equal'     → equal_bg    / ...
分类 'clear'     → clear_bg    / ...
分类 'sci'       → sci_bg      / ...
分类 'paren'     → paren_bg    / ...
```

每个按钮使用 `tk.Button(relief=FLAT, borderwidth=0)` 实现扁平无边框风格。按钮创建后注册到 `_buttons` 列表，主题切换时遍历全部按钮更新配色。

### 3.7 `gui/history_panel.py` — 历史记录面板

默认隐藏，点击工具栏 `History` 按钮后显示在左侧（宽度 190px）。

```
┌──────────────┐
│ History      │  ← 标题 (Label)
├──────────────┤
│ 3+5 = 8     │  ← Listbox (可滚动)
│ sin(pi) = 0 │
│ 2**10 = 1024│
│ ...         │
├──────────────┤
│[Clear History]│ ← 清除按钮
└──────────────┘
```

| 交互 | 行为 |
|---|---|
| 双击列表项 | 回调 `on_recall(result)`，将结果回填到显示屏 |
| Clear History | 调用 `history.clear()` 清空内存和文件 |

显示格式：`"{expression} = {result}"`，最新记录在顶部（`reversed` 遍历）。

### 3.8 `gui/main_window.py` — 主控制器

**职责**：编排所有 GUI 组件，实现按钮逻辑和键盘绑定，是应用的核心枢纽。

#### 状态机

```
                        ┌──────────┐
         按任意键        │          │  按数字
    ┌─────────────────→│  input   │←─────────┐
    │    (开始新表达式)  │ (构建表达式)│  按运算符  │
    │                   │          │ (用结果续算)│
    │                   └────┬─────┘           │
    │                        │ 按 =            │
    │                   ┌────▼─────┐           │
    │                   │  result  │───────────┘
    │                   │ (显示结果) │
    │   按数字/函数/清空  └────┬─────┘
    └─────────────────────────┘
```

**两种模式**：

| 模式 | 含义 | 按数字 | 按运算符 | 按 = |
|---|---|---|---|---|
| `input` | 正在构建表达式 | 追加到表达式 | 追加到表达式 | 求值，切换到 result |
| `result` | 刚完成计算 | 清空，开始新表达式 | 用结果 + 运算符开头 | 不做操作 |

#### 按钮字符 → 内部动作映射 (DISPATCH)

按钮显示 Unicode 数学符号，点击后通过 `DISPATCH` 转换为内部动作：

| 按钮显示 | Unicode | 内部动作 | 说明 |
|---|---|---|---|
| `÷` | `\u00f7` | `/` | 除法 |
| `×` | `\u00d7` | `*` | 乘法 |
| `−` | `\u2212` | `-` | 减法 |
| `⌫` | `\u232b` | `backspace` | 退格 |
| `π` | `\u03c0` | `pi` | 圆周率 |
| `√` | `\u221a` | `sqrt(` | 平方根 |
| `±` | `\u00b1` | `negate` | 正负号 |
| `x²` | `x\u00b2` | `sq` | 平方(后缀) |
| `xⁿ` | `x\u207f` | `pow_open` | 幂运算(前缀) |
| `¹/x` | `\u00b9/x` | `recip` | 倒数(后缀) |

#### 后缀运算符算法 (`_wrap_last_operand`)

用于 `x²`、`n!`、`¹/x` 等需要包裹最后一个操作数的按钮。

```
输入: prefix="**2", suffix=""  (x² 按钮)
示例表达式: "3+5"

算法:
  1. 从末尾扫描: '5'→'3'→'+' (停止，'+' 不在 [0-9.pi e] 中)
  2. i=1, inner = expr[2:] = "5"
  3. i>=0: return expr[:2] + "(" + "5" + ")" + "**2" = "3+(5)**2"

示例表达式: "sin(45)"
  1. 末尾是 ')': 括号匹配 → 找到 '(' 在位置 3
  2. inner = "(45)"
  3. '(' 前有 "sin" 函数名
  4. return "sin(45)**2"

示例表达式: "5"
  1. 扫描: '5' → i=-1 (全串扫描完)
  2. i<0: return "5" + "**2" = "5**2"
```

#### 正负号切换 (`_toggle_sign`)

```
输入: "3+5"
  1. 从末尾扫描数字: '5'→'+' (停止)
  2. num_start=2, 前一个字符 '+' 不是 '-'

输入: "(-5)"
  1. 从末尾扫描: ')' 不是数字 → 无匹配，返回原串

简化策略: 仅对纯数字结尾的表达式生效
```

#### 键盘映射

通过 `root.bind_all('<Key>', handler)` 全局捕获按键：

| 物理按键 | 触发动作 |
|---|---|
| `0-9`, `.`, `(`, `)` | 直接追加字符 |
| `+`, `-`, `*`, `/` | 追加对应运算符 |
| `Enter` / `KP_Enter` | 求值 (`=`) |
| `BackSpace` | 退格 (`⌫`) |
| `Escape` | 全部清除 (`CA`) |
| `Delete` | 清除当前 (`C`) |
| `p` | 插入 π |
| `e` | 插入 e |
| `^` | 插入 `**(` |

修饰键 `Ctrl/Alt/Shift/Tab` 等被过滤，不触发任何动作。

---

## 4. 数据流

### 完整交互流程（用户点击 `3 + 5 =`）

```
用户点击 [3]
  → ButtonGrid._build() 中 lambda 触发 _on_click('3')
  → main_window._on_button('3')
    → DISPATCH.get('3', '3') = '3'  (无特殊映射)
    → mode='input' → self._expression += '3'
    → _refresh_display() → display.set_expression('3')

用户点击 [+]
  → _on_button('+')
    → DISPATCH.get('+', '+') = '+'
    → self._expression = '3+'
    → _refresh_display()

用户点击 [5]
  → self._expression = '3+5'
  → _refresh_display()

用户点击 [=]
  → _on_button('=')
    → action='=' → _evaluate()
      → safe_eval('3+5') → compile → eval → '8'
      → display.set_expression('3+5 =')
      → display.set_result('8')
      → mode='result', result='8'
      → history.add('3+5', '8') → 写入 history.json
      → _refresh_history() → 如果历史面板可见，更新 listbox
```

### 主题切换流程

```
用户点击 Theme 按钮
  → _toggle_theme()
    → theme_mgr.toggle() → 切换 _current 引用
    → _notify() → 遍历 listeners:
      ├── Display._apply_theme(theme)    → 更新标签背景/前景
      ├── ButtonGrid._apply_theme(theme) → 遍历所有按钮更新配色
      └── HistoryPanel._apply_theme(theme)→ 更新列表/标题配色
    → _apply_theme(theme) → root.configure(bg=theme['bg'])
```

---

## 5. 项目文件清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `app.py` | 17 | 程序入口 |
| `core/__init__.py` | 1 | 包标识 |
| `core/calculator.py` | 55 | 安全表达式求值 |
| `core/history.py` | 52 | 历史数据模型与持久化 |
| `gui/__init__.py` | 1 | 包标识 |
| `gui/theme_manager.py` | 79 | 主题定义 + 观察者通知 |
| `gui/display.py` | 51 | 双行显示屏 |
| `gui/button_grid.py` | 136 | 按钮网格布局 + 配色 |
| `gui/history_panel.py` | 81 | 历史记录侧栏 |
| `gui/main_window.py` | 347 | 主控制器（状态机、键盘、按钮逻辑） |
| **合计** | **~820** | |

---

## 6. 安全设计

| 威胁 | 防护 |
|---|---|
| `eval` 注入 (`__import__('os').system('rm')`) | `{'__builtins__': {}}` 禁用所有内置函数 |
| 未授权模块访问 | `compile` + `co_names` 白名单校验 |
| 非数学对象注入 (`open('file')`) | 编译时拒绝不在白名单中的名称 |
| 文件写入失败导致崩溃 | `history.save()` 异常静默捕获 |
| 超大数据/死循环 | Python 表达式语法限制（无 while/for），`factorial` 输入自然受限 |

---

## 7. 扩展点

| 扩展方向 | 修改点 |
|---|---|
| 新增数学函数 | 在 `calculator.py:namespace` 添加映射 |
| 新增按钮 | 在 `button_grid.py:BUTTON_ROWS` 添加定义 + `main_window.py:DISPATCH` 添加映射 |
| 新增主题色板 | 在 `theme_manager.py` 添加新主题字典 |
| 角度/弧度模式切换 | 在 `main_window` 添加模式标志，`safe_eval` 中根据标志做 `radians()` 转换 |
| 打包为 exe | `pip install pyinstaller && pyinstaller --onefile --name calculator calculator/app.py` |
