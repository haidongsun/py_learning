import tkinter as tk
from typing import Callable, List, Tuple

ButtonDef = Tuple[str, str, int]  # text, category, rowspan

BUTTON_ROWS: List[List[ButtonDef]] = [
    [
        ('C',    'clear',    1),
        ('CA',   'clear',    1),
        ('\u232b', 'clear',  1),
        ('\u00f7', 'operator', 1),
        ('%',    'sci',      1),
    ],
    [
        ('7',    'number',   1),
        ('8',    'number',   1),
        ('9',    'number',   1),
        ('\u00d7', 'operator', 1),
        ('sin',  'sci',      1),
    ],
    [
        ('4',    'number',   1),
        ('5',    'number',   1),
        ('6',    'number',   1),
        ('\u2212', 'operator', 1),
        ('cos',  'sci',      1),
    ],
    [
        ('1',    'number',   1),
        ('2',    'number',   1),
        ('3',    'number',   1),
        ('+',    'operator', 1),
        ('tan',  'sci',      1),
    ],
    [
        ('\u00b1', 'sci',    1),
        ('0',    'number',   1),
        ('.',    'number',   1),
        ('(',    'paren',    1),
        (')',    'paren',    1),
    ],
    [
        ('\u03c0', 'sci',    1),
        ('e',    'sci',      1),
        ('x\u00b2', 'sci',   1),
        ('\u221a', 'sci',    1),
        ('=',    'equal',    2),
    ],
    [
        ('x\u207f', 'sci',   1),
        ('\u00b9/x', 'sci',  1),
        ('n!',   'sci',      1),
        ('ln',   'sci',      1),
    ],
]

CATEGORY_BG = {
    'number':   'number_bg',
    'operator': 'operator_bg',
    'equal':    'equal_bg',
    'clear':    'clear_bg',
    'sci':      'sci_bg',
    'paren':    'paren_bg',
}

CATEGORY_FG = {
    'number':   'number_fg',
    'operator': 'operator_fg',
    'equal':    'equal_fg',
    'clear':    'clear_fg',
    'sci':      'sci_fg',
    'paren':    'paren_fg',
}

CATEGORY_ACTIVE = {
    'number':   'number_active_bg',
    'operator': 'operator_active_bg',
    'equal':    'equal_active_bg',
    'clear':    'clear_active_bg',
    'sci':      'sci_active_bg',
    'paren':    'paren_active_bg',
}

NUM_TEXT = set('0123456789')


class ButtonGrid(tk.Frame):
    def __init__(self, parent, theme_manager, on_click: Callable, **kwargs):
        super().__init__(parent, **kwargs)
        self._theme_mgr = theme_manager
        self._on_click = on_click
        self._buttons: List[Tuple[tk.Button, str, str]] = []

        self._build()
        self._apply_theme(theme_manager.theme)
        theme_manager.subscribe(self._apply_theme)

    def _build(self):
        for col in range(5):
            self.columnconfigure(col, weight=1, uniform='btn_col')

        r = 0
        for row_def in BUTTON_ROWS:
            self.rowconfigure(r, weight=1, uniform='btn_row')
            c = 0
            for btn_def in row_def:
                if btn_def is None:
                    c += 1
                    continue
                text, category, rowspan = btn_def

                font_size = 18 if text in NUM_TEXT or text in ('.',) else 15
                font_weight = 'bold' if category in ('operator', 'equal') else 'normal'

                btn = tk.Button(
                    self, text=text,
                    font=('Segoe UI', font_size, font_weight),
                    relief=tk.FLAT, borderwidth=0,
                    padx=6, pady=8,
                    command=lambda t=text: self._on_click(t),
                )
                btn.grid(row=r, column=c, rowspan=rowspan, sticky='nsew', padx=2, pady=2)
                self._buttons.append((btn, category, text))
                c += 1
            r += 1

    def _apply_theme(self, theme):
        for btn, category, text in self._buttons:
            bg_key = CATEGORY_BG.get(category, 'number_bg')
            fg_key = CATEGORY_FG.get(category, 'number_fg')
            active_key = CATEGORY_ACTIVE.get(category, 'number_active_bg')

            bg = theme.get(bg_key, '#E0E0E0')
            fg = theme.get(fg_key, '#202020')
            active_bg = theme.get(active_key, bg)

            btn.configure(
                bg=bg, fg=fg,
                activebackground=active_bg, activeforeground=fg,
                disabledforeground=fg,
            )
