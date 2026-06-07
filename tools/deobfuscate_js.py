"""
通用 JS 去混淆脚本 — 覆盖最常见的前端混淆模式。

用法:
    python deobfuscate_js.py input.js [output.js]

功能:
    1. 字符串数组还原 (_0x1234('0xa') → "原文")
    2. 简单 eval/unpack 展开
    3. 格式化/美化
    4. 导出 webpack 模块（方便按模块查看）

局限:
    - 不处理控制流平坦化、VM 保护、严重混淆
    - 适合国内常见的字符串数组 + eval 或 webpack 打包场景
"""

import re
import sys
import ast
import os
from pathlib import Path


# ───────────────────── 工具函数 ─────────────────────

def safe_eval_js_array(code: str) -> list | None:
    """试图从 JS 代码中提取字符串数组并安全求值。"""
    # 模式1: var _0x1234 = ['abc','def',...];
    m = re.search(r'var\s+(\w+)\s*=\s*\[([^\]]*(?:\][^\]]*)*?)\]\s*;', code, re.DOTALL)
    if not m:
        # 模式2: const _0x = ['abc','def',...];
        m = re.search(r'const\s+(\w+)\s*=\s*\[([^\]]*(?:\][^\]]*)*?)\]\s*;', code, re.DOTALL)
    if not m:
        # 模式3: _0x1234 = ['abc',...];
        m = re.search(r'(\w+)\s*=\s*\[([^\]]*(?:\][^\]]*)*?)\]\s*;', code, re.DOTALL)

    if m:
        arr_name = m.group(1)
        arr_content = m.group(2)
        try:
            raw = '[' + arr_content.replace("\n", "") + ']'
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list) and len(parsed) > 3:
                return parsed, arr_name
        except (SyntaxError, ValueError):
            pass
    return None


def find_lookup_function(code: str, arr_name: str) -> str | None:
    """找到字符串查找函数，返回函数名。"""
    # 模式: function _0x1234(_0xabc, _0xdef) { ... return _0xname[_0xabc - 0x1a2]; }
    # 或: var _0x1234 = function(a,b){...}
    patterns = [
        rf'function\s+(\w+)\s*\([^)]*\)\s*\{{\s*[^}}]*{arr_name}',
        rf'var\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*\{{\s*[^}}]*{arr_name}',
        rf'(\w+)\s*=\s*function\s*\([^)]*\)\s*\{{\s*[^}}]*{arr_name}',
    ]
    for pat in patterns:
        m = re.search(pat, code)
        if m:
            return m.group(1)
    return None


def extract_shift_amount(lookup_body: str) -> int | None:
    """从查找函数体中提取偏移量。"""
    # _0xname[_0xabc - 0x1a2] → 0x1a2
    m = re.search(r'-\s*(0x[0-9a-fA-F]+)', lookup_body)
    if m:
        return int(m.group(1), 16)
    # _0xname[_0xabc - 123] → 123
    m = re.search(r'-\s*(\d+)', lookup_body)
    if m:
        return int(m.group(1))
    return None


def replace_string_calls(code: str, strings: list, func_name: str, shift: int = 0) -> str:
    """将 func_name('0x1a') 替换为实际字符串。"""
    def replacer(m):
        arg = m.group(1)
        try:
            if arg.startswith('0x') or arg.startswith('0X'):
                idx = int(arg, 16) - shift
            else:
                idx = int(arg) - shift
            if 0 <= idx < len(strings):
                s = strings[idx]
                return repr(s)  # 用 repr 保证引号和转义
        except (ValueError, IndexError):
            pass
        return m.group(0)

    # 匹配: func_name('0x1a') 或 func_name("0x1a") 或 func_name(0x1a)
    pattern = rf'{re.escape(func_name)}\s*\(\s*(["\']?)([^"\'()]+)\1\s*\)'
    return re.sub(pattern, replacer, code)


def unpack_evals(code: str, max_depth: int = 5) -> str:
    """递归展开 eval(...) 和 Function(...) 包装。"""
    for _ in range(max_depth):
        # 匹配 eval("code") 或 eval('code')
        m = re.search(r'eval\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)', code)
        if m:
            try:
                inner = m.group(1).encode().decode('unicode_escape')
                code = code.replace(m.group(0), inner)
                continue
            except Exception:
                break

        # 匹配: (function() { ... }())
        m = re.search(r'[\w$]*\s*=\s*function\s*\(\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}\s*\(\s*\)', code)
        if m:
            continue  # 太复杂，跳过

        break
    return code


def export_webpack_modules(code: str, out_dir: str):
    """将 webpack 打包的模块拆分成独立文件。"""
    # webpack 典型格式: { 123: function(e,t,n){...}, 456: function(e,t,n){...} }
    m = re.search(r'(\{(\s*\d+\s*:\s*function[^}]*\},?\s*)+\})', code)
    if not m:
        # 也可能是键是字符串的
        pass

    # 找到模块对象
    module_block = re.search(
        r'(?:var\s+\w+\s*=\s*)?(\{\s*\d+\s*:\s*function)',
        code
    )
    if not module_block:
        print("  未识别 webpack 模块模式")
        return

    # 简单尝试提取各个模块
    modules = re.findall(
        r'(\d+)\s*:\s*function\s*\(([^)]*)\)\s*\{(.*?)\}\s*,?\s*(?=\d+\s*:|[\}\)])',
        code, re.DOTALL
    )

    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for mod_id, params, body in modules:
        fname = os.path.join(out_dir, f"module_{mod_id}.js")
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(f"// module {mod_id}\n")
            f.write(f"function({params}) {{\n{body}\n}}\n")
        count += 1

    print(f"  导出 {count} 个 webpack 模块到 {out_dir}/")


# ───────────────────── 主流程 ─────────────────────

def deobfuscate(input_path: str, output_path: str | None = None):
    with open(input_path, 'r', encoding='utf-8') as f:
        code = f.read()

    original_size = len(code)

    # ── 步骤1: 展开 eval ──
    code = unpack_evals(code)
    if len(code) != original_size:
        print(f"  [OK] eval 展开完成 ({original_size} → {len(code)} 字符)")

    # ── 步骤2: 提取字符串数组 ──
    result = safe_eval_js_array(code)
    if result is None:
        print("  [!!] 未找到字符串数组（可能不需要此步骤）")
    else:
        strings, arr_name = result
        print(f"  找到字符串数组: {arr_name} ({len(strings)} 项)")

        # ── 步骤3: 找到查找函数 ──
        func_name = find_lookup_function(code, arr_name)

        if func_name:
            print(f"  找到查找函数: {func_name}")

            # 提取偏移量
            shift = 0
            func_match = re.search(
                rf'function\s+{re.escape(func_name)}\s*\([^)]*\)\s*\{{([^}}]+)\}}',
                code
            )
            if not func_match:
                func_match = re.search(
                    rf'{re.escape(func_name)}\s*=\s*function\s*\([^)]*\)\s*\{{([^}}]+)\}}',
                    code
                )
            if func_match:
                shift = extract_shift_amount(func_match.group(1)) or 0
                print(f"  偏移量: {shift}")

            # ── 步骤4: 替换所有字符串调用 ──
            code = replace_string_calls(code, strings, func_name, shift)
            print(f"  字符串还原完成")

        # ── 步骤5: 再展开一遍 eval（字符串还原后可能有新的）
        code = unpack_evals(code)
        if len(code) != original_size:
            print(f"  [OK] 二次 eval 展开完成")

    # ── 步骤6: 尝试识别并导出 webpack 模块 ──
    out_dir = os.path.join(os.path.dirname(input_path) or '.', 'webpack_modules')
    export_webpack_modules(code, out_dir)

    # ── 步骤7: 输出结果 ──
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = base + '.clean' + ext

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"\n  输出: {output_path} ({len(code)} 字符)")
    print(f"  提示: 用 Prettier 或 IDE 格式化一下效果更好")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python deobfuscate_js.py input.js [output.js]")
        print("示例: python deobfuscate_js.py app.ef123.js")
        sys.exit(1)

    deobfuscate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
