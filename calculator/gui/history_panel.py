import tkinter as tk


class HistoryPanel(tk.Frame):
    def __init__(self, parent, history_store, theme_manager, on_recall, **kwargs):
        super().__init__(parent, **kwargs)
        self._history = history_store
        self._theme_mgr = theme_manager
        self._on_recall = on_recall
        self._build()
        self._apply_theme(theme_manager.theme)
        theme_manager.subscribe(self._apply_theme)

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)

        self._title_label = tk.Label(
            self, text='History',
            font=('Segoe UI', 13, 'bold'),
            anchor='w',
        )
        self._title_label.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 6))

        list_frame = tk.Frame(self)
        list_frame.grid(row=1, column=0, sticky='nsew', padx=8, pady=4)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._listbox = tk.Listbox(
            list_frame, font=('Segoe UI', 11),
            selectmode=tk.SINGLE, borderwidth=0,
            highlightthickness=0, activestyle='none',
        )
        self._listbox.grid(row=0, column=0, sticky='nsew')

        scrollbar = tk.Scrollbar(
            list_frame, orient='vertical',
            command=self._listbox.yview,
            borderwidth=0,
        )
        scrollbar.grid(row=0, column=1, sticky='ns')
        self._listbox.configure(yscrollcommand=scrollbar.set)

        self._listbox.bind('<Double-Button-1>', self._on_double_click)

        self._clear_btn = tk.Button(
            self, text='Clear History',
            font=('Segoe UI', 11),
            relief=tk.FLAT, borderwidth=0, padx=8, pady=6,
            command=self._clear,
        )
        self._clear_btn.grid(row=2, column=0, sticky='ew', padx=12, pady=(0, 12))

    def _on_double_click(self, event):
        selection = self._listbox.curselection()
        if selection:
            index = len(self._history.entries) - 1 - selection[0]
            try:
                entry = self._history.entries[index]
                self._on_recall(entry.result)
            except IndexError:
                pass

    def _clear(self):
        self._history.clear()
        self.refresh()

    def refresh(self):
        self._listbox.delete(0, tk.END)
        for entry in reversed(self._history.entries):
            self._listbox.insert(tk.END, f'{entry.expression} = {entry.result}')

    def _apply_theme(self, theme):
        bg = theme['bg']
        fg = theme['display_fg']
        sci_bg = theme.get('sci_bg', '#D6D6D6')
        sci_fg = theme.get('sci_fg', '#202020')
        display_bg = theme.get('display_bg', '#FFFFFF')
        display_bg_faded = self._darken(display_bg, 0.06)

        self.configure(bg=bg)
        self._title_label.configure(bg=bg, fg=fg)
        self._listbox.configure(
            bg=display_bg_faded, fg=fg,
            selectbackground=theme['operator_bg'],
            selectforeground=theme['operator_fg'],
        )
        self._clear_btn.configure(
            bg=sci_bg, fg=sci_fg,
            activebackground=theme.get('sci_active_bg', sci_bg),
            activeforeground=sci_fg,
        )

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip('#')
        if not hex_color:
            return '#E8E8E8'
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f'#{r:02x}{g:02x}{b:02x}'
