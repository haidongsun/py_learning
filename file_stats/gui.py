import os
import shutil
import subprocess
import sys
import time
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def fmt_size(n):
    if n < 1024:
        return f"{n} B"
    for u in _UNITS[1:]:
        n /= 1024.0
        if n < 1024:
            return f"{n:.1f} {u}"
    return f"{n:.1f} PB"


def fmt_mtime(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _dir_size_with_cache(dirpath, cache):
    """Returns (total_size, file_count, dir_mtime). Populates cache with flat listings."""
    total = 0
    file_count = 0
    items = []
    dir_mtime = 0
    try:
        with os.scandir(dirpath) as it:
            for entry in it:
                name = entry.name
                if name.startswith('.'):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    sub_total, sub_count, _ = _dir_size_with_cache(entry.path, cache)
                    total += sub_total
                    file_count += sub_count
                    try:
                        mt = entry.stat(follow_symlinks=False).st_mtime
                    except OSError:
                        mt = 0
                    items.append((name, sub_total, True, sub_count, mt))
                elif entry.is_file(follow_symlinks=False):
                    try:
                        st = entry.stat(follow_symlinks=False)
                        sz = st.st_size
                        mt = st.st_mtime
                    except OSError:
                        continue
                    total += sz
                    file_count += 1
                    items.append((name, sz, False, 1, mt))
    except OSError:
        pass
    try:
        dir_mtime = os.stat(dirpath).st_mtime
    except OSError:
        pass
    items.sort(key=lambda x: x[1], reverse=True)
    cache[dirpath] = (items, file_count)
    return total, file_count, dir_mtime


def scan_flat(dirpath, cache, parallel=False):
    """Returns (items, total_file_count). Populates cache for all subdirectories."""
    items = []
    total_files = 0
    dir_tasks = []

    try:
        with os.scandir(dirpath) as it:
            for entry in it:
                name = entry.name
                if name.startswith('.'):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    dir_tasks.append((entry.path, name))
                elif entry.is_file(follow_symlinks=False):
                    try:
                        st = entry.stat(follow_symlinks=False)
                        sz = st.st_size
                        mt = st.st_mtime
                    except OSError:
                        continue
                    total_files += 1
                    items.append((name, sz, False, 1, mt))
    except OSError:
        pass

    if dir_tasks:
        if parallel and len(dir_tasks) > 2:
            with ThreadPoolExecutor(max_workers=min(len(dir_tasks), (os.cpu_count() or 4))) as pool:
                futures = {pool.submit(_dir_size_with_cache, d[0], cache): d for d in dir_tasks}
                for fut in as_completed(futures):
                    name = futures[fut][1]
                    sz, fc, mt = fut.result()
                    total_files += fc
                    items.append((name, sz, True, fc, mt))
        else:
            for dpath, name in dir_tasks:
                sz, fc, mt = _dir_size_with_cache(dpath, cache)
                total_files += fc
                items.append((name, sz, True, fc, mt))

    items.sort(key=lambda x: x[1], reverse=True)
    cache[dirpath] = (items, total_files)
    return items, total_files


class FileStatsApp:
    def __init__(self, start_dir="."):
        self.root = tk.Tk()
        self.root.title("File Stats — Disk Usage Analyzer")
        self.root.geometry("960x640")
        self.root.minsize(700, 400)

        self.current_dir = os.path.abspath(start_dir)
        self.items = []
        self.total_files = 0
        self.total_size = 0
        self._cache = {}
        self._scanning = False
        self.sort_col = "size_raw"
        self.sort_reverse = True

        self._build_ui()
        self._navigate(self.current_dir)

    def _build_ui(self):
        # ── Top toolbar ──
        toolbar = ttk.Frame(self.root, padding=(8, 8, 8, 0))
        toolbar.pack(fill=tk.X)

        path_row = ttk.Frame(toolbar)
        path_row.pack(fill=tk.X)
        ttk.Label(path_row, text="Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(path_row, textvariable=self.path_var)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        path_entry.bind("<Return>", lambda e: self._navigate(self.path_var.get()))
        ttk.Button(path_row, text="Browse...", command=self._browse).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(path_row, text="Go", command=lambda: self._navigate(self.path_var.get())).pack(side=tk.LEFT)

        action_row = ttk.Frame(toolbar)
        action_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(action_row, text="\u2191  Up", command=self._go_up).pack(side=tk.LEFT)
        ttk.Button(action_row, text="\u21bb  Refresh", command=self._refresh).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(action_row, text="\u2302  Root", command=self._go_root).pack(side=tk.LEFT, padx=(4, 0))
        self.parallel_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(action_row, text="Parallel", variable=self.parallel_var).pack(side=tk.RIGHT)

        # ── Navigation bar ──
        nav = ttk.Frame(self.root, padding=(8, 4))
        nav.pack(fill=tk.X)
        self.nav_label = ttk.Label(nav, text="", font=("Consolas", 9))
        self.nav_label.pack(side=tk.LEFT)

        # ── Treeview ──
        tree_frame = ttk.Frame(self.root, padding=(8, 0))
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame,
                                 columns=("name", "size_raw", "size", "files", "share", "modified", "type"),
                                 show="headings", selectmode="browse")
        self.tree.heading("name", text="Name", command=lambda: self._sort("name"))
        self.tree.heading("size_raw", text="", command=lambda: self._sort("size_raw"))
        self.tree.heading("size", text="Size", command=lambda: self._sort("size_raw"))
        self.tree.heading("files", text="Files", command=lambda: self._sort("files"))
        self.tree.heading("share", text="Share", command=lambda: self._sort("size_raw"))
        self.tree.heading("modified", text="Modified", command=lambda: self._sort("modified"))
        self.tree.heading("type", text="", command=lambda: self._sort("type"))

        self.tree.column("name", width=250, minwidth=100)
        self.tree.column("size_raw", width=0, minwidth=0, stretch=False)
        self.tree.column("size", width=90, minwidth=70, anchor=tk.E)
        self.tree.column("files", width=60, minwidth=45, anchor=tk.E)
        self.tree.column("share", width=130, minwidth=80, anchor=tk.CENTER)
        self.tree.column("modified", width=110, minwidth=90, anchor=tk.CENTER)
        self.tree.column("type", width=50, minwidth=40, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", self._on_double_click)
        self.tree.bind("<BackSpace>", lambda e: (self._scanning or self._go_up()))
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.tag_configure("dir", foreground="#1565C0")
        self.tree.tag_configure("file", foreground="#424242")

        # ── Status bar ──
        self.status = ttk.Label(self.root, text="Ready", padding=(8, 4), relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _navigate(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            messagebox.showerror("Error", f"Not a directory:\n{path}")
            return

        self.current_dir = path
        self.path_var.set(path)
        self.nav_label.configure(text=f"  {path}")
        self.tree.delete(*self.tree.get_children())
        self.root.update_idletasks()

        cached = self._cache.get(path)
        if cached is not None:
            self.items, self.total_files = cached
            self.total_size = sum(sz for _, sz, *_ in self.items)
            self._populate()
            self.status.configure(
                text=f"  {len(self.items)} items  |  {self.total_files} files  |  {fmt_size(self.total_size)}  |  (cached)")
            return

        self.status.configure(text="  Scanning...")
        self._set_buttons_state(tk.DISABLED)

        parallel = self.parallel_var.get()

        def _bg_scan():
            t0 = time.perf_counter()
            try:
                result_items, result_files = scan_flat(path, self._cache, parallel=parallel)
            except Exception as e:
                self.root.after(0, self._scan_error, str(e))
                return
            t1 = time.perf_counter()
            elapsed = (t1 - t0) * 1000
            self.root.after(0, self._scan_done, result_items, result_files, elapsed)

        self._scanning = True
        threading.Thread(target=_bg_scan, daemon=True).start()

    def _scan_done(self, items, total_files, elapsed):
        self._scanning = False
        self._set_buttons_state(tk.NORMAL)
        self.items = items
        self.total_files = total_files
        self.total_size = sum(sz for _, sz, *_ in items)
        self._populate()
        self.status.configure(
            text=f"  {len(items)} items  |  {total_files} files  |  {fmt_size(self.total_size)}  |  {elapsed:.1f} ms")

    def _scan_error(self, msg):
        self._scanning = False
        self._set_buttons_state(tk.NORMAL)
        self.status.configure(text=f"  Error: {msg}")

    def _set_buttons_state(self, state):
        for child in self.root.winfo_children():
            if isinstance(child, tk.Frame):
                for widget in child.winfo_children():
                    if isinstance(widget, (ttk.Button, ttk.Entry, ttk.Checkbutton)):
                        try:
                            widget.configure(state=state)
                        except tk.TclError:
                            pass

    def _populate(self):
        self.tree.delete(*self.tree.get_children())
        items = self.items
        if self.sort_col == "name":
            items = sorted(self.items, key=lambda x: x[0].lower(), reverse=self.sort_reverse)
        elif self.sort_col == "size_raw":
            items = sorted(self.items, key=lambda x: x[1], reverse=self.sort_reverse)
        elif self.sort_col == "files":
            items = sorted(self.items, key=lambda x: x[3], reverse=self.sort_reverse)
        elif self.sort_col == "type":
            items = sorted(self.items, key=lambda x: (not x[2], x[0].lower()), reverse=self.sort_reverse)
        elif self.sort_col == "modified":
            items = sorted(self.items, key=lambda x: x[4], reverse=self.sort_reverse)

        total = self.total_size
        for i, (name, sz, is_dir, fc, mt) in enumerate(items):
            tag = "dir" if is_dir else "file"
            kind = "\U0001F4C1" if is_dir else "\U0001F4C4"
            pct = (sz / total * 100) if total else 0
            bar_len = max(1, int(pct / 5))
            bar = "\u2588" * min(bar_len, 10)
            share_text = f"{bar} {pct:.1f}%"
            mtime_str = fmt_mtime(mt) if mt else "-"
            self.tree.insert("", tk.END, iid=str(i),
                             values=(name, sz, fmt_size(sz), fc, share_text, mtime_str, kind), tags=(tag,))

    def _sort(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = col in ("size_raw", "files", "modified")
        self._populate()

    def _on_double_click(self, event):
        if self._scanning:
            return
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self.items):
            name, _, is_dir, *_ = self.items[idx]
            if is_dir:
                new_path = os.path.join(self.current_dir, name)
                self._navigate(new_path)

    def _on_right_click(self, event):
        if self._scanning:
            return
        sel = self.tree.selection()
        if sel:
            # select the row under cursor first
            row = self.tree.identify_row(event.y)
            if row:
                self.tree.selection_set(row)
                idx = int(row)
            else:
                return
        else:
            return

        name, _, is_dir, *_ = self.items[idx]
        full_path = os.path.join(self.current_dir, name)

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Open", command=lambda: os.startfile(full_path))
        menu.add_command(label="Open in Explorer",
                         command=lambda: subprocess.Popen(['explorer', '/select,', full_path]))
        menu.add_separator()
        menu.add_command(label="Copy Path",
                         command=lambda: self._copy_to_clipboard(full_path))
        menu.add_separator()
        menu.add_command(label="Delete", command=lambda: self._delete_item(full_path, is_dir))
        menu.add_separator()
        menu.add_command(label="Open Current Folder",
                         command=lambda: os.startfile(self.current_dir))
        menu.add_command(label="Copy Current Folder Path",
                         command=lambda: self._copy_to_clipboard(self.current_dir))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _delete_item(self, path, is_dir):
        name = os.path.basename(path)
        msg = f"Permanently delete '{name}'?" if not is_dir else f"Permanently delete folder '{name}' and all contents?"
        if not messagebox.askyesno("Confirm Delete", msg, icon="warning"):
            return
        try:
            if is_dir:
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete:\n{e}")
            return
        self._cache.pop(self.current_dir, None)
        self._cache.pop(path, None)
        self._navigate(self.current_dir)

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status.configure(text=f"  Copied: {text}")

    def _go_up(self):
        if self._scanning:
            return
        parent = os.path.dirname(self.current_dir)
        if parent and parent != self.current_dir:
            self._navigate(parent)

    def _go_root(self):
        if self._scanning:
            return
        drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
        if drives:
            self._navigate(drives[0])
        else:
            self._navigate(os.path.abspath(os.sep))

    def _refresh(self):
        if self._scanning:
            return
        self._cache.pop(self.current_dir, None)
        self._navigate(self.current_dir)

    def _browse(self):
        if self._scanning:
            return
        d = filedialog.askdirectory(initialdir=self.current_dir, title="Select Directory")
        if d:
            self._navigate(d)

    def run(self):
        self.root.mainloop()


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "."
    app = FileStatsApp(start)
    app.run()


if __name__ == "__main__":
    main()
