"""
通用 JS 去混淆脚本 — 支持单文件和整个目录（多 JS 文件拆分场景）。

用法:
    python deobfuscate_js.py input.js [output.js]        # 单文件
    python deobfuscate_js.py js_source_dir/              # 整个目录

多文件模式:
    1. 先扫描所有 .js 文件，收集全局混淆上下文（字符串数组 + 查表函数）
    2. 再逐文件应用还原（本文件的 + 跨文件的，串联全局作用域）
    3. 输出到 cleaned/ 子目录，保持原有目录结构
"""

import re
import sys
import ast
import os
import json
from pathlib import Path


# ───────────────────── 基础工具 ─────────────────────

def safe_eval_js_array(code: str):
    """提取 JS 字符串数组并安全解析返回 (strings_list, var_name)。"""
    patterns = [
        r'(?:var|const|let)\s+(\w+)\s*=\s*(\[[^\]]*(?:\][^\]]*)*?\])\s*;',
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
    """找到引用指定数组的查表函数名。"""
    patterns = [
        rf'function\s+(\w+)\s*\([^)]*\)\s*\{{[^}}]*\b{arr_name}\b',
        rf'(?:var|const|let)\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*\{{[^}}]*\b{arr_name}\b',
        rf'(\w+)\s*=\s*function\s*\([^)]*\)\s*\{{[^}}]*\b{arr_name}\b',
    ]
    for pat in patterns:
        m = re.search(pat, code)
        if m:
            return m.group(1)
    return None


def extract_shift_amount(func_body: str) -> int:
    m = re.search(r'-\s*(0x[0-9a-fA-F]+)', func_body)
    if m:
        return int(m.group(1), 16)
    m = re.search(r'-\s*(\d+)', func_body)
    if m:
        return int(m.group(1))
    return 0


def replace_string_calls(code: str, strings: list, func_name: str, shift: int = 0) -> str:
    """将 func_name('idx') 替换为实际字符串。"""
    def replacer(m):
        arg = m.group(2)
        try:
            if arg.startswith(('0x', '0X')):
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


# ───────────────────── webpack 模块拆分 ─────────────────────

def bracket_extract(text: str, start_pos: int) -> tuple[str, int]:
    """用深度计数提取大括号内容，处理嵌套和字符串字面量。"""
    depth = 0
    i = start_pos
    while i < len(text):
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start_pos:i], i + 1
        elif c in ('"', "'"):
            q = c
            i += 1
            while i < len(text) and text[i] != q:
                if text[i] == '\\':
                    i += 1
                i += 1
        i += 1
    return "", -1


def parse_webpack_modules(code: str) -> dict:
    m = re.search(r'\{\s*(["\']?)(\d+|[./\w-]+)\1\s*:\s*function\s*\(([^)]*)\)\s*\{', code)
    if not m:
        return {}

    obj_start = code.index(m.group(0))
    modules_code, obj_end = bracket_extract(code, obj_start)
    if not modules_code:
        return {}

    modules = {}
    pos = 0
    content = modules_code.strip()

    while pos < len(content):
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
            key_match = re.match(
                r'\s*(["\']?)([^"\':,\s]+)\1\s*:\s*(?:function\s*)?\(([^)]*)\)\s*=>',
                content[pos:], re.DOTALL
            )
            if not key_match:
                pos += 1
                continue

        mod_id = key_match.group(2)
        params = key_match.group(3)

        brace_start = pos + key_match.start(4)
        body, brace_end = bracket_extract(content, brace_start)
        if brace_end == -1:
            pos += len(key_match.group(0))
            continue

        full_body = content[brace_start + 1:brace_end - 1]
        param_list = [p.strip() for p in params.split(',')]
        require_name = param_list[2] if len(param_list) >= 3 else 'n'

        requires = []
        for rm in re.finditer(rf'\b{re.escape(require_name)}\s*\(\s*(\d+)\s*\)', full_body):
            requires.append(rm.group(1))

        modules[mod_id] = {
            'body': full_body.strip(),
            'requires': list(set(requires)),
            'params': params,
            'require_name': require_name,
        }
        pos = brace_end + 1

    return modules


def resolve_require_calls(modules: dict) -> dict:
    resolved = {}
    name_map = {}
    for mid in modules:
        if mid.startswith('./') or mid.startswith('../'):
            name_map[mid] = mid
        else:
            name_map[mid] = f"module_{mid}"

    for mod_id, info in modules.items():
        body = info['body']
        rname = info['require_name']

        def replacer(m):
            rid = m.group(1)
            label = name_map.get(rid, f"module_{rid}")
            return f'{rname}({rid}) /* → {label} */'

        body = re.sub(rf'\b{re.escape(rname)}\s*\(\s*(\d+)\s*\)', replacer, body)
        resolved[mod_id] = {**info, 'body': body}
    return resolved


def export_webpack_to_files(code: str, input_path: str, strings=None, func_name=None, shift=0):
    """解析 webpack 模块并导出为独立文件 + 依赖图。"""
    modules = parse_webpack_modules(code)
    if not modules:
        return None

    if strings and func_name:
        for mod_id in modules:
            modules[mod_id]['body'] = replace_string_calls(
                modules[mod_id]['body'], strings, func_name, shift
            )

    modules = resolve_require_calls(modules)
    depgraph = {mid: info['requires'] for mid, info in modules.items()}

    parent = os.path.dirname(input_path) or '.'
    out_dir = os.path.join(parent, 'webpack_modules')
    os.makedirs(out_dir, exist_ok=True)

    for mod_id, info in modules.items():
        deps_comment = ""
        if info['requires']:
            deps_comment = f"// depends on: [{', '.join(info['requires'])}]\n"

        safe_name = re.sub(r'[<>:"/\\|?*]', '_', mod_id)
        fname = os.path.join(out_dir, f"{safe_name}.js")
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(f"// module: {mod_id}\n")
            f.write(f"// (module, exports, require) = ({info['params']})\n")
            f.write(deps_comment)
            f.write(f"// {'='*48}\n\n")
            f.write(info['body'])
            f.write("\n")

    with open(os.path.join(out_dir, '.depgraph.json'), 'w', encoding='utf-8') as f:
        json.dump(depgraph, f, indent=2, ensure_ascii=False)

    return modules


# ───────────────────── 多文件扫描 & 上下文 ─────────────────────

def scan_file_for_context(filepath: str) -> list[dict]:
    """
    扫描单个 JS 文件，提取所有混淆上下文。
    返回: [{strings, func_name, shift, arr_name}, ...]
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    contexts = []
    result = safe_eval_js_array(code)
    if not result:
        return contexts

    strings, arr_name = result
    func_name = find_lookup_function(code, arr_name)
    if not func_name:
        return contexts

    shift = 0
    for pat in [
        rf'function\s+{re.escape(func_name)}\s*\([^)]*\)\s*\{{([^}}]+)\}}',
        rf'{re.escape(func_name)}\s*=\s*function\s*\([^)]*\)\s*\{{([^}}]+)\}}',
    ]:
        fm = re.search(pat, code)
        if fm:
            shift = extract_shift_amount(fm.group(1))
            break

    contexts.append({
        'strings': strings,
        'func_name': func_name,
        'shift': shift,
        'arr_name': arr_name,
        'source_file': filepath,
    })

    return contexts


def scan_directory(dirpath: str) -> dict[str, list[dict]]:
    """
    扫描目录下所有 .js 文件，返回全局混淆上下文:
        { filepath: [context1, context2, ...], ... }
    """
    all_contexts = {}
    for root, dirs, files in os.walk(dirpath):
        # 跳过输出目录
        dirs[:] = [d for d in dirs if d not in ('cleaned', 'webpack_modules', '.git', 'node_modules')]
        for fname in files:
            if fname.endswith('.js'):
                fpath = os.path.join(root, fname)
                ctx = scan_file_for_context(fpath)
                if ctx:
                    all_contexts[fpath] = ctx
    return all_contexts


def build_global_context_map(file_contexts: dict[str, list[dict]]) -> dict[str, dict]:
    """
    构建 "查表函数名 → 完整上下文" 的全局映射。
    跨文件共享时，靠函数名匹配。
    """
    global_map = {}
    for contexts in file_contexts.values():
        for ctx in contexts:
            key = ctx['func_name']
            if key not in global_map:
                global_map[key] = ctx
    return global_map


# ───────────────────── 主流程 ─────────────────────

def deobfuscate_single(input_path: str, output_path: str | None = None):
    """单文件模式。"""
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    original_size = len(code)
    print(f"  输入: {input_path} ({original_size} 字符)\n")

    # ① 展开 eval
    code = unpack_evals(code)
    if len(code) != original_size:
        print(f"  [1] eval 展开: {original_size} → {len(code)} 字符")

    # ② 字符串还原
    strings, func_name, shift = None, None, 0
    result = safe_eval_js_array(code)
    if result:
        strings, arr_name = result
        func_name = find_lookup_function(code, arr_name)
        if func_name:
            print(f"  [2] 字符串数组: {arr_name} ({len(strings)} 项), 查表函数: {func_name}")

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
            code = unpack_evals(code)
            print(f"  [2] 字符串还原完成")
    else:
        print(f"  [2] 未找到字符串数组（跳过）")

    # ③ webpack 拆分
    print(f"\n  [3] 尝试 webpack 模块拆分...")
    modules = export_webpack_to_files(code, input_path, strings, func_name, shift)
    if modules:
        print(f"  [3] 导出 {len(modules)} 个模块 → webpack_modules/")
    else:
        print(f"  [3] 未识别到 webpack 结构")

    # ④ 输出
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = base + '.clean' + ext

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"\n  [✓] 输出: {output_path} ({len(code)} 字符)")


def deobfuscate_directory(dirpath: str):
    """多文件目录模式 —— 先扫描全局上下文，再逐文件还原。"""
    print(f"  [0] 扫描目录: {dirpath}\n")

    # ── 阶段 1: 全局扫描 ──
    print(f"  [1] 扫描所有 .js 文件，收集混淆上下文...")
    file_contexts = scan_directory(dirpath)
    global_map = build_global_context_map(file_contexts)

    context_files = []
    for fpath, ctxs in file_contexts.items():
        for ctx in ctxs:
            context_files.append(f"    {os.path.relpath(fpath, dirpath)}: {ctx['func_name']}() ← [{ctx['arr_name']}] x{len(ctx['strings'])}")

    if context_files:
        print(f"  [1] 发现 {len(context_files)} 个混淆上下文:")
        for cf in context_files:
            print(cf)
    else:
        print(f"  [1] 未发现任何混淆上下文，仅做 eval 展开")

    print(f"\n  [1] 全局查表函数映射: {list(global_map.keys())}")

    # ── 阶段 2: 收集所有需要处理的文件 ──
    all_files = []
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in ('cleaned', 'webpack_modules', '.git', 'node_modules')]
        for fname in files:
            if fname.endswith('.js'):
                all_files.append(os.path.join(root, fname))

    print(f"\n  [2] 处理 {len(all_files)} 个文件...\n")

    # ── 阶段 3: 逐文件还原 ──
    out_dir = os.path.join(dirpath, 'cleaned')
    os.makedirs(out_dir, exist_ok=True)
    webpack_root = os.path.join(out_dir, 'webpack_modules')

    stats = {'processed': 0, 'strings_replaced': 0, 'eval_unpacked': 0}

    for fpath in all_files:
        rel = os.path.relpath(fpath, dirpath)
        out_path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        original_size = len(code)

        # 3a: 展开 eval
        code = unpack_evals(code)
        if len(code) != original_size:
            stats['eval_unpacked'] += 1

        # 3b: 应用所有全局上下文中的字符串还原
        any_replaced = False
        for func_name, ctx in global_map.items():
            # 检查当前文件中是否使用了这个查表函数
            if re.search(rf'\b{re.escape(func_name)}\s*\(', code):
                code = replace_string_calls(code, ctx['strings'], func_name, ctx['shift'])
                any_replaced = True

        if any_replaced:
            stats['strings_replaced'] += 1
            code = unpack_evals(code)  # 还原后可能有新的 eval 可展开

        # 3c: 尝试 webpack 拆分（只在含模块结构的文件中）
        modules = parse_webpack_modules(code)
        if modules:
            # 对模块再应用一次字符串还原
            if any_replaced:
                for func_name, ctx in global_map.items():
                    for mod_id in modules:
                        modules[mod_id]['body'] = replace_string_calls(
                            modules[mod_id]['body'], ctx['strings'], func_name, ctx['shift']
                        )
            modules = resolve_require_calls(modules)

            # 导出模块文件
            safe_rel = re.sub(r'[<>:"|?*]', '_', rel)
            mod_dir = os.path.join(webpack_root, os.path.splitext(safe_rel.replace(os.sep, '_'))[0])
            os.makedirs(mod_dir, exist_ok=True)

            for mod_id, info in modules.items():
                deps_comment = ""
                if info['requires']:
                    deps_comment = f"// depends on: [{', '.join(info['requires'])}]\n"
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', mod_id)
                with open(os.path.join(mod_dir, f"{safe_name}.js"), 'w', encoding='utf-8') as mf:
                    mf.write(f"// module: {mod_id}\n")
                    mf.write(f"// (module, exports, require) = ({info['params']})\n")
                    mf.write(deps_comment)
                    mf.write(f"// {'='*48}\n\n")
                    mf.write(info['body'])
                    mf.write("\n")

            depgraph = {mid: info['requires'] for mid, info in modules.items()}
            with open(os.path.join(mod_dir, '.depgraph.json'), 'w', encoding='utf-8') as df:
                json.dump(depgraph, df, indent=2, ensure_ascii=False)

            print(f"  {rel}: {len(modules)} webpack 模块 → {mod_dir}/")

        # 3d: 输出清理后的文件
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(code)
        stats['processed'] += 1

    # ── 阶段 4: 报告 ──
    print(f"\n  {'='*60}")
    print(f"  [✓] 处理完成: {stats['processed']} 个文件")
    print(f"  [✓] 字符串还原: {stats['strings_replaced']} 个文件")
    print(f"  [✓] eval 展开: {stats['eval_unpacked']} 个文件")
    print(f"  [✓] 输出目录: {out_dir}/")
    print(f"  [✓] 下一步: npx prettier --write \"{out_dir}/**/*.js\"")


# ───────────────────── 入口 ─────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = sys.argv[1]

    if os.path.isdir(target):
        deobfuscate_directory(target)
    elif os.path.isfile(target):
        output = sys.argv[2] if len(sys.argv) > 2 else None
        deobfuscate_single(target, output)
    else:
        print(f"错误: 找不到 '{target}' (不是文件也不是目录)")
        sys.exit(1)
