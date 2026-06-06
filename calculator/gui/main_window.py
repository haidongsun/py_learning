import tkinter as tk
from calculator.gui.theme_manager import ThemeManager
from calculator.gui.display import Display
from calculator.gui.button_grid import ButtonGrid
from calculator.gui.history_panel import HistoryPanel
from calculator.core.calculator import safe_eval
from calculator.core.history import HistoryStore

DISPATCH = {
    'C':          'clear',
    'CA':         'clear_all',
    '\u232b':     'backspace',
    '\u00f7':     '/',
    '\u00d7':     '*',
    '\u2212':     '-',
    '\u03c0':     'pi',
    '\u00b1':     'negate',
    '\u221a':     'sqrt(',
    'x\u00b2':    'sq',
    'x\u207f':    'pow_open',
    '\u00b9/x':   'recip',
    'sin':        'sin(',
    'cos':        'cos(',
    'tan':        'tan(',
    'log':        'log(',
    'ln':         'ln(',
    'n!':         'factorial(',
}

AFTER_RESULT_NEW = {'clear', 'clear_all', 'backspace'}
AFTER_RESULT_OPERATOR = {'+', '-', '*', '/'}
AFTER_RESULT_DIGIT = set('0123456789.')


class CalculatorApp:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._root.title('Calculator')
        self._root.geometry('420x640')
        self._root.minsize(340, 520)

        self._expression = ''
        self._mode = 'input'
        self._result = ''

        self._history = HistoryStore()
        self._theme_mgr = ThemeManager()

        self._build()
        self._apply_theme(self._theme_mgr.theme)
        self._theme_mgr.subscribe(self._apply_theme)
        self._setup_keyboard()
        self._refresh_history()

    def _build(self):
        self._root.columnconfigure(0, weight=0)
        self._root.columnconfigure(1, weight=1)
        self._root.rowconfigure(0, weight=1)

        # History panel (left, hidden by default)
        self._history_panel = HistoryPanel(
            self._root, self._history, self._theme_mgr,
            on_recall=self._on_history_recall,
            width=220
        )
        self._history_visible = False

        # Main area (right)
        self._main_frame = tk.Frame(self._root)
        self._main_frame.grid(row=0, column=1, sticky='nsew', padx=8, pady=8)
        self._main_frame.columnconfigure(0, weight=1)

        # Toolbar
        self._toolbar = tk.Frame(self._main_frame)
        self._toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        self._toolbar.columnconfigure(0, weight=1)
        self._toolbar.columnconfigure(1, weight=1)

        self._history_btn = tk.Button(
            self._toolbar, text='\u2630  History',
            font=('Segoe UI', 11),
            relief=tk.FLAT, borderwidth=0, padx=10, pady=3,
            command=self._toggle_history,
        )
        self._history_btn.grid(row=0, column=0, sticky='w')

        self._theme_btn = tk.Button(
            self._toolbar, text='\u2600  Light',
            font=('Segoe UI', 11),
            relief=tk.FLAT, borderwidth=0, padx=10, pady=3,
            command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=1, sticky='e')

        # Display
        self._display = Display(self._main_frame, self._theme_mgr)
        self._display.grid(row=1, column=0, sticky='ew', pady=(0, 8))

        # Button grid
        self._button_grid = ButtonGrid(
            self._main_frame, self._theme_mgr,
            on_click=self._on_button
        )
        self._button_grid.grid(row=2, column=0, sticky='nsew')
        self._main_frame.rowconfigure(2, weight=1)

    def _toggle_history(self):
        if self._history_visible:
            self._history_panel.grid_forget()
            self._history_visible = False
        else:
            self._history_panel.grid(row=0, column=0, sticky='nsew', padx=(8, 0), pady=8)
            self._history_panel.refresh()
            self._history_visible = True

    def _toggle_theme(self):
        self._theme_mgr.toggle()
        theme = self._theme_mgr.theme
        self._theme_btn.configure(
            text='\u263e  Dark' if theme['name'] == 'Dark' else '\u2600  Light'
        )
        self._apply_theme(theme)

    def _apply_theme(self, theme):
        self._root.configure(bg=theme['bg'])
        toolbar_bg = theme.get('toolbar_bg', theme['bg'])
        self._toolbar.configure(bg=toolbar_bg)
        btn_fg = theme.get('display_fg', '#1C1C1E')
        self._history_btn.configure(
            bg=toolbar_bg, fg=btn_fg,
            activebackground=self._lighten(toolbar_bg),
            activeforeground=btn_fg,
        )
        self._theme_btn.configure(
            bg=toolbar_bg, fg=btn_fg,
            activebackground=self._lighten(toolbar_bg),
            activeforeground=btn_fg,
        )

    @staticmethod
    def _lighten(hex_color: str) -> str:
        hex_color = hex_color.lstrip('#')
        if not hex_color:
            return '#D0D0D0'
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, r + 30)
        g = min(255, g + 30)
        b = min(255, b + 30)
        return f'#{r:02x}{g:02x}{b:02x}'

    def _on_button(self, char: str):
        action = DISPATCH.get(char, char)

        if action == 'clear':
            self._expression = ''
            self._mode = 'input'
            self._result = ''
            self._display.set_expression('')
            self._display.set_result('0')
            return

        if action == 'clear_all':
            self._expression = ''
            self._mode = 'input'
            self._result = ''
            self._display.set_expression('')
            self._display.set_result('0')
            return

        if action == 'backspace':
            if self._mode == 'input' and self._expression:
                self._expression = self._expression[:-1]
                self._refresh_display()
            return

        if action == '=':
            self._evaluate()
            return

        if self._mode == 'result':
            if action in AFTER_RESULT_NEW:
                self._expression = ''
                self._result = ''
                self._mode = 'input'
            elif action in AFTER_RESULT_OPERATOR:
                if self._result and not self._result.startswith('Error'):
                    self._expression = self._result + action
                    self._result = ''
                    self._mode = 'input'
                    self._refresh_display()
                return
            elif action in AFTER_RESULT_DIGIT:
                self._expression = ''
                self._result = ''
                self._mode = 'input'
            else:
                self._expression = ''
                self._result = ''
                self._mode = 'input'

        if action == 'negate':
            self._expression = self._toggle_sign(self._expression)
        elif action == 'sq':
            self._expression = self._wrap_last_operand('**2')
        elif action == 'pow_open':
            self._expression += '**('
        elif action == 'recip':
            self._expression = self._wrap_last_operand('1/(', ')')
        elif action == 'pi':
            self._expression += 'pi'
        elif action == 'e':
            self._expression += 'e'
        elif action == 'factorial(':
            self._expression = self._wrap_last_operand('factorial(', ')')
        elif action == 'sqrt(':
            self._expression += 'sqrt('
        elif action in ('sin(', 'cos(', 'tan(', 'log(', 'ln('):
            self._expression += action
        elif action in ('!',):
            self._expression += '!'
        else:
            self._expression += action

        self._refresh_display()

    def _wrap_last_operand(self, prefix: str, suffix: str = '') -> str:
        expr = self._expression
        if not expr:
            return prefix + suffix

        i = len(expr) - 1
        last_ch = expr[i]

        if last_ch == ')':
            depth = 1
            i -= 1
            while i >= 0 and depth > 0:
                if expr[i] == ')':
                    depth += 1
                elif expr[i] == '(':
                    depth -= 1
                i -= 1
            inner = expr[i + 1:]
            k = i
            while k >= 0 and expr[k].isalpha():
                k -= 1
            func_name = expr[k + 1:i + 1]
            if func_name:
                return expr[:k + 1] + func_name + inner + prefix + suffix
            return expr[:i + 1] + inner + prefix + suffix

        if last_ch in '0123456789.pie':
            while i >= 0 and expr[i] in '0123456789.pie':
                i -= 1
            inner = expr[i + 1:]
            if i < 0:
                return expr + prefix + suffix
            return expr[:i + 1] + '(' + inner + ')' + prefix + suffix

        return expr + prefix + suffix

    def _toggle_sign(self, expr: str) -> str:
        if not expr:
            return '-'
        i = len(expr) - 1
        while i >= 0 and expr[i] in '0123456789.':
            i -= 1
        if i < 0:
            return expr[1:] if expr.startswith('-') else '-' + expr

        num_start = i + 1
        if num_start == len(expr):
            return expr

        is_neg = num_start > 0 and expr[num_start - 1] == '-'
        if is_neg:
            before = expr[num_start - 2] if num_start >= 2 else ''
            if before in '+*/(' or num_start == 1:
                return expr[:num_start - 1] + expr[num_start:]

        if num_start > 0 and expr[num_start - 1] in '+*/(':
            return expr[:num_start] + '-' + expr[num_start:]
        else:
            return expr[:num_start] + '(-' + expr[num_start:] + ')'

    def _evaluate(self):
        if not self._expression:
            return
        result = safe_eval(self._expression)
        self._display.set_expression(self._expression + ' =')
        self._display.set_result(result)
        self._mode = 'result'
        self._result = result
        if not result.startswith('Error'):
            self._history.add(self._expression, result)
            self._refresh_history()

    def _refresh_display(self):
        self._display.set_expression(self._expression)
        self._display.set_result('')

    def _refresh_history(self):
        if self._history_visible:
            self._history_panel.refresh()

    def _on_history_recall(self, result: str):
        self._expression = result
        self._mode = 'result'
        self._result = result
        self._display.set_expression(result)
        self._display.set_result(result)

    def _setup_keyboard(self):
        self._root.bind_all('<Key>', self._on_key, add='+')

    def _on_key(self, event):
        keysym = event.keysym
        char = event.char

        if keysym in ('Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R',
                       'Tab', 'Caps_Lock', 'Num_Lock', 'Scroll_Lock'):
            return

        if keysym in ('Return', 'KP_Enter'):
            self._on_button('=')
            return
        if keysym == 'BackSpace':
            self._on_button('\u232b')
            return
        if keysym == 'Escape':
            self._on_button('CA')
            return
        if keysym == 'Delete':
            self._on_button('C')
            return

        if keysym in ('slash', 'division'):
            self._on_button('\u00f7')
            return
        if keysym == 'asterisk':
            self._on_button('\u00d7')
            return
        if keysym == 'minus':
            self._on_button('\u2212')
            return
        if keysym == 'plus':
            self._on_button('+')
            return
        if keysym == 'period':
            self._on_button('.')
            return
        if keysym == 'comma':
            self._on_button('.')
            return
        if keysym == 'percent':
            self._on_button('%')
            return

        if char and char in '0123456789()^':
            if char == '^':
                self._on_button('x\u207f')
            else:
                self._on_button(char)
            return

        if char and char.lower() == 'p':
            self._on_button('\u03c0')
            return
        if char and char.lower() == 'e':
            self._on_button('e')
            return
