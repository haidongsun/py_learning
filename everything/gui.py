"""Tkinter GUI for the Everything search engine.

Usage:  python -m everything.gui
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from everything.everything import Everything, _CATEGORY_LABELS
else:
    from .everything import Everything, _CATEGORY_LABELS


_LABEL_TO_CATEGORY = {label.lower(): key for key, label in _CATEGORY_LABELS}
_CATEGORY_DISPLAY = [''] + [label for _, label in _CATEGORY_LABELS]


class EverythingGUI:
    def __init__(self):
        self._engine = Everything()
        self._root = tk.Tk()
        self._root.title('PyEverything')
        self._root.geometry('800x500')

        self._build_ui()
        self._start_indexing()

    # --- UI construction ----------------------------------------------------

    def _build_ui(self):
        frame = ttk.Frame(self._root, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        # search entry
        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill=tk.X)
        ttk.Label(entry_frame, text='Search:').pack(side=tk.LEFT)
        self._query_var = tk.StringVar()
        self._query_var.trace_add('write', self._on_query_change)
        self._entry = ttk.Entry(entry_frame, textvariable=self._query_var)
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self._entry.focus_set()

        ttk.Label(entry_frame, text=' Type:').pack(side=tk.LEFT, padx=(8, 0))
        self._ext_var = tk.StringVar()
        self._ext_var.trace_add('write', self._on_query_change)
        self._ext_combo = ttk.Combobox(
            entry_frame, textvariable=self._ext_var,
            values=_CATEGORY_DISPLAY, width=14, state='normal',
        )
        self._ext_combo.pack(side=tk.LEFT, padx=(4, 0))

        # result list
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self._listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 10),
            activestyle='none',
        )
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self._listbox.yview
        )
        self._listbox.config(yscrollcommand=scrollbar.set)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.bind('<Double-Button-1>', self._on_double_click)

        # status bar
        self._status_var = tk.StringVar(value='Indexing...')
        status = ttk.Label(frame, textvariable=self._status_var, relief=tk.SUNKEN)
        status.pack(fill=tk.X, pady=(4, 0))

        self._root.bind('<Control-q>', lambda e: self._root.destroy())

    # --- Indexing (background) ----------------------------------------------

    def _start_indexing(self):
        t = threading.Thread(target=self._index_thread, daemon=True)
        t.start()

    def _index_thread(self):
        drives = [f'{l}:\\' for l in 'ABCDEFGHIJ' if os.path.exists(f'{l}:\\')]
        total = 0
        for i, d in enumerate(drives):
            self._root.after(0, self._status_var.set,
                             f'Scanning {d} ({i+1}/{len(drives)})...')
            n, _ = self._engine.index_directory(d)
            total += n
        self._root.after(0, self._on_index_done, total)

    def _on_index_done(self, total):
        self._status_var.set(f'Ready - {total:,} files indexed')
        self._on_query_change()

    # --- Search -------------------------------------------------------------

    def _on_query_change(self, *args):
        query = self._query_var.get().strip()
        type_text = self._ext_var.get().strip().lower()
        self._listbox.delete(0, tk.END)
        if (not query and not type_text) or self._engine.total_files == 0:
            return
        cat = _LABEL_TO_CATEGORY.get(type_text, '')
        ext = '' if cat else type_text
        results = self._engine.search(query, ext=ext, category=cat, limit=200)
        for p in results:
            self._listbox.insert(tk.END, p)
        cnt = len(results)
        self._status_var.set(
            f'{cnt} results  |  Index: {self._engine.total_files:,} files'
        )

    def _on_double_click(self, event):
        sel = self._listbox.curselection()
        if sel:
            path = self._listbox.get(sel[0])
            os.startfile(os.path.dirname(path))

    # --- Run ----------------------------------------------------------------

    def run(self):
        self._root.mainloop()


def main():
    gui = EverythingGUI()
    gui.run()


if __name__ == '__main__':
    main()
