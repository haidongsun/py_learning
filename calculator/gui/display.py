import tkinter as tk


class Display(tk.Frame):
    def __init__(self, parent, theme_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self._theme_mgr = theme_manager
        self._build()
        self._apply_theme(theme_manager.theme)
        theme_manager.subscribe(self._apply_theme)

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._border = tk.Frame(self, bd=1, relief='solid')
        self._border.grid(row=0, column=0, sticky='nsew')
        self._border.columnconfigure(0, weight=1)
        self._border.rowconfigure(0, weight=0)
        self._border.rowconfigure(1, weight=1)

        self.expr_var = tk.StringVar(value='')
        self.expr_label = tk.Label(
            self._border,
            textvariable=self.expr_var,
            anchor='e',
            font=('Segoe UI', 12),
            wraplength=500,
        )
        self.expr_label.grid(row=0, column=0, sticky='ew', padx=12, pady=(8, 0))

        self.result_var = tk.StringVar(value='0')
        self.result_label = tk.Label(
            self._border,
            textvariable=self.result_var,
            anchor='e',
            font=('Segoe UI', 36, 'bold'),
        )
        self.result_label.grid(row=1, column=0, sticky='ew', padx=12, pady=(0, 8))

    def set_expression(self, text: str):
        self.expr_var.set(text)

    def set_result(self, text: str):
        self.result_var.set(text)

    def _apply_theme(self, theme):
        self.configure(bg=theme['bg'])
        self._border.configure(bg=theme['display_border'])
        self.expr_label.configure(
            bg=theme['display_bg'],
            fg=theme.get('display_expr_fg', '#8E8E93'),
        )
        self.result_label.configure(
            bg=theme['display_bg'],
            fg=theme['display_fg'],
        )
