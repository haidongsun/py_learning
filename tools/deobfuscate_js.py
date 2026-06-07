"""
通用 JS 去混淆脚本 — 覆盖最常见的前端混淆模式。

用法:
    python deobfuscate_js.py input.js [output.js]

增强的 webpack 拆分:
    1. 识别模块原始路径（如 ./src/utils.js）
    2. 模块内 require(n) 自动解析为可读引用
    3. 生成依赖图 (.depgraph)
    4. 每个模块独立再做一轮字符串还原
"""

import re
import sys
import ast
import os
import json
from pathlib import Path


# ───────────────────── 工具函数 ─────────────────────

def safe_eval_js_array(code: str):
    """试图从 JS 代码中提取字符串数组并安全求值。"""
    patterns = [
        r'var\s+(\w+)\s*=\s*(\[[^\]]*(?:\][^\]]*)*?\])\s*;',
        r'const\s+(\w+)\s*=\s*(\[[^\]]*(?:\][^\]]*)*?\])\s*;',
        r'(\w+)\s*=\s*(\[[^\]]*(?:\][^\]]*)*?\])\s*;',
    ]
    for pat in patterns:
        m = re.search(pat, code, re.DOTALL)
        if m:
            arr_name = m.group(1)
            arr_content = m.group(2)
            try:
                raw = arr_content.replace("\n", "").replace("\r", "")
                parsed = ast.literal_eval(raw)
                if isinstance(parsed, list) and len(parsed) > 3:
                    return parsed, arr_name
            except (SyntaxError, ValueError):
                pass
    return None


def find_lookup_function(code: str, arr_name: str) -> str | None:
    patterns = [
        rf'function\s+(\w+)\s*\([^)]*\)\s*\{{[^}}]*{arr_name}',
        rf'var\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*\{{[^}}]*{arr_name}',
        rf'(\w+)\s*=\s*function\s*\([^)]*\)\s*\{{[^}}]*{arr_name}',
    ]
    for pat in patterns:
        m = re.search(pat, code)
        if m:
            return m.group(1)
    return None


def extract_shift_amount(lookup_body: str) -> int:
    m = re.search(r'-\s*(0x[0-9a-fA-F]+)', lookup_body)
    if m:
        return int(m.group(1), 16)
    m = re.search(r'-\s*(\d+)', lookup_body)
    if m:
        return int(m.group(1))
    return 0


def replace_string_calls(code: str, strings: list, func_name: str, shift: int = 0) -> str:
    def replacer(m):
        arg = m.group(2)
        try:
            if arg.startswith('0x') or arg.startswith('0X'):
                idx = int(arg, 16) - shift
            else:
                idx = int(arg) - shift
            if 0 <= idx < len(strings):
                return repr(strings[idx])
        except (ValueError, IndexError):
            pass
        return m.group(0)

    pattern = rf'{re.escape(func_name)}\s*\(\s*(["\']?)([^"\'()]+)\1\s*\)'
    return re.sub(pattern, replacer, code)


def unpack_evals(code: str, max_depth: int = 5) -> str:
    for _ in range(max_depth):
        m = re.search(r'eval\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)', code)
        if m:
            try:
                inner = m.group(1).encode().decode('unicode_escape')
                code = code.replace(m.group(0), inner)
                continue
            except Exception:
                break
        break
    return code


# ───────────────────── Webpack 模块解析 ─────────────────────

def bracket_extract(text: str, start_pos: int) -> tuple[str, int]:
    """从 start_pos 处提取一对大括号内的内容（处理嵌套），返回(内容, 结束位置)。"""
    depth = 0
    i = start_pos
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start_pos:i], i + 1
        elif text[i] == '"' or text[i] == "'":
            q = text[i]
            i += 1
            while i < len(text) and text[i] != q:
                if text[i] == '\\':
                    i += 1
                i += 1
            continue
        i += 1
    return "", -1


def parse_webpack_modules(code: str) -> dict:
    """
    解析 webpack 模块对象，返回:
        { module_id: { body, requires, original_name } }
    
    module_id 可能是数字字符串或路径字符串。
    requires 是该模块中调用的其他模块 ID 列表。
    """
    # 查找模块对象起始: { 123: or { "./src/":
    m = re.search(r'\{\s*(["\']?)(\d+|[./\w-]+)\1\s*:\s*function\s*\(([^)]*)\)\s*\{', code)
    if not m:
        return {}

    # 从这里开始用 bracket 计数解析整个对象
    obj_start = code.index(m.group(0))  # 开头的 {
    modules_code, obj_end = bracket_extract(code, obj_start)
    if not modules_code:
        return {}

    modules = {}
    # 解析键值对: key: function(params){ body }
    # 用简单的 split-on-key 方式
    pos = 0
    content = modules_code.strip()
    
    while pos < len(content):
        # 匹配键: "key" 或 'key' 或 key
        key_match = re.match(
            r'\s*(["\']?)([^"\':,\s]+)\1\s*:\s*function\s*\(([^)]*)\)\s*(\{)',
            content[pos:], re.DOTALL
        )
        if not key_match:
            key_match = re.match(
                r'\s*(["\']?)([^"\':,\s]+)\1\s*:\s*(?:function\s*)?\(([^)]*)\)\s*=>\s*(\{)',
                content[pos:], re.DOTALL
            )
        if not key_match:
            # 可能是箭头函数没有花括号
            key_match = re.match(
                r'\s*(["\']?)([^"\':,\s]+)\1\s*:\s*(?:function\s*)?\(([^)]*)\)\s*=>',
                content[pos:], re.DOTALL
            )
            if key_match:
                # 箭头函数直接返回，匹配到分号或逗号
                simple = True
            else:
                pos += 1
                continue
        
        mod_id = key_match.group(2)
        params = key_match.group(3)
        
        # 找到函数体
        brace_start = pos + key_match.start(4)
        body, brace_end = bracket_extract(content, brace_start)
        if brace_end == -1:
            pos += len(key_match.group(0))
            continue

        full_body = content[brace_start + 1:brace_end - 1]  # 去掉外层花括号
        
        # 提取 require 参数名（通常是第三个参数）
        param_list = [p.strip() for p in params.split(',')]
        require_name = param_list[2] if len(param_list) >= 3 else 'n'

        # 在函数体中找所有 require(name) 调用
        requires = []
        for rm in re.finditer(rf'\b{re.escape(require_name)}\s*\(\s*(\d+)\s*\)', full_body):
            requires.append(rm.group(1))

        modules[mod_id] = {
            'body': full_body.strip(),
            'requires': list(set(requires)),
            'params': params,
            'require_name': require_name,
        }
        
        pos = brace_end + 1  # 跳过 }

    return modules


def resolve_require_calls(modules: dict) -> dict:
    """将每个模块内的 require(123) 替换为 /* module_123 */ 注释标记。"""
    resolved = {}
    for mod_id, info in modules.items():
        body = info['body']
        rname = info['require_name']
        # 构建模块名映射（尝试用原始路径名）
        name_map = {}
        for mid in modules:
            if mid.startswith('./') or mid.startswith('../'):
                name_map[mid] = mid
            else:
                name_map[mid] = f"module_{mid}"
        
        def replacer(m):
            rid = m.group(1)
            label = name_map.get(rid, f"module_{rid}")
            return f'{rname}({rid}) /* → {label} */'
        
        body = re.sub(rf'\b{re.escape(rname)}\s*\(\s*(\d+)\s*\)', replacer, body)
        resolved[mod_id] = {**info, 'body': body}
    return resolved


def build_depgraph(modules: dict) -> dict:
    """构建依赖关系图。"""
    graph = {}
    for mod_id, info in modules.items():
        graph[mod_id] = info['requires']
    return graph


def extract_chunk_name(code: str, module_id: str) -> str:
    """尝试从代码上下文中找到模块 ID 对应的原始路径名。
    Webpack 有时在 push 时会传入路径映射。
    """
    # 模式: webpackJsonp([1], {"./src/app.js": function(...) { ... }})
    # 或模块映射表
    patterns = [
        # 直接路径键
        rf'["\']({re.escape(module_id)})["\']',
        # 数字到路径映射
        rf'{re.escape(module_id)}\s*:\s*["\']([^"\']+)["\']',
        rf'["\']([^"\']+)["\']\s*:\s*{re.escape(module_id)}',
    ]
    # 简单返回 module_id 本身（如果它已经是路径）
    return module_id


# ───────────────────── 主流程 ─────────────────────

def deobfuscate(input_path: str, output_path: str | None = None):
    with open(input_path, 'r', encoding='utf-8') as f:
        code = f.read()

    original_size = len(code)
    print(f"  输入: {input_path} ({original_size} 字符)\n")

    # ── 步骤1: 展开 eval ──
    code = unpack_evals(code)
    if len(code) != original_size:
        print(f"  [1] eval 展开完成 ({original_size} → {len(code)} 字符)")

    # ── 步骤2: 提取字符串数组 ──
    result = safe_eval_js_array(code)
    strings = None
    func_name = None
    shift = 0

    if result:
        strings, arr_name = result
        print(f"  [2] 找到字符串数组: {arr_name} ({len(strings)} 项)")

        func_name = find_lookup_function(code, arr_name)
        if func_name:
            print(f"  [2] 找到查找函数: {func_name}")
            for pat in [
                rf'function\s+{re.escape(func_name)}\s*\([^)]*\)\s*\{{([^}}]+)\}}',
                rf'{re.escape(func_name)}\s*=\s*function\s*\([^)]*\)\s*\{{([^}}]+)\}}',
            ]:
                fm = re.search(pat, code)
                if fm:
                    shift = extract_shift_amount(fm.group(1))
                    break
            print(f"  [2] 偏移量: {shift}")

            code = replace_string_calls(code, strings, func_name, shift)
            print(f"  [2] 字符串还原完成")

            code = unpack_evals(code)
    else:
        print(f"  [2] 未找到字符串数组（跳过）")

    # ── 步骤3: 解析 webpack 模块 ──
    print(f"\n  [3] 解析 webpack 模块...")
    modules = parse_webpack_modules(code)

    if not modules:
        print(f"  [3] 未识别到 webpack 模块结构")
    else:
        # 再对每个模块应用字符串还原
        if strings and func_name:
            for mod_id in modules:
                modules[mod_id]['body'] = replace_string_calls(
                    modules[mod_id]['body'], strings, func_name, shift
                )

        # 解析 require 调用为可读引用
        modules = resolve_require_calls(modules)

        # 生成依赖图
        depgraph = build_depgraph(modules)

        # 导出模块
        out_dir = os.path.join(os.path.dirname(input_path) or '.', 'webpack_modules')
        os.makedirs(out_dir, exist_ok=True)

        for mod_id, info in modules.items():
            # 生成本地变量注释
            params = [p.strip() for p in info['params'].split(',')]
            param_comment = f"// module, exports, require = ({info['params']})"
            deps_comment = ""
            if info['requires']:
                deps = ', '.join(info['requires'])
                deps_comment = f"// depends on: [{deps}]"

            safe_name = re.sub(r'[<>:"/\\|?*]', '_', mod_id)
            fname = os.path.join(out_dir, f"{safe_name}.js")
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"// module: {mod_id}\n")
                f.write(param_comment + "\n")
                if deps_comment:
                    f.write(deps_comment + "\n")
                f.write("// ================================================\n\n")
                f.write(info['body'])
                f.write("\n")

        # 保存依赖图
        depgraph_path = os.path.join(out_dir, '.depgraph.json')
        with open(depgraph_path, 'w', encoding='utf-8') as f:
            json.dump(depgraph, f, indent=2, ensure_ascii=False)

        print(f"  [3] 导出 {len(modules)} 个 webpack 模块 → {out_dir}/")
        print(f"  [3] 依赖图 → {depgraph_path}")

        # 替换原文件中的 require 调用
        if func_name and strings:
            rname_map = {info['require_name'] for info in modules.values()}
            for rn in rname_map:
                def make_replacer(rn=rn):
                    def replacer(m):
                        rid = m.group(1)
                        return f'{rn}({rid}) /* → module_{rid} */'
                    return replacer
                code = re.sub(rf'\b{re.escape(rn)}\s*\(\s*(\d+)\s*\)', make_replacer(), code)

    # ── 步骤4: 输出结果 ──
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = base + '.clean' + ext

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"\n  [✓] 输出去混淆文件: {output_path} ({len(code)} 字符)")
    print(f"  [✓] 下一步: npx prettier --write {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python deobfuscate_js.py input.js [output.js]")
        print("示例: python deobfuscate_js.py app.ef123.js")
        sys.exit(1)

    deobfuscate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
