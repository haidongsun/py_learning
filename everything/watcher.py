import ctypes
from ctypes import wintypes
import os
import threading


FILE_LIST_DIRECTORY = 0x0001
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_OVERLAPPED = 0x40000000

FILE_ACTION_ADDED = 0x00000001
FILE_ACTION_REMOVED = 0x00000002
FILE_ACTION_MODIFIED = 0x00000003
FILE_ACTION_RENAMED_OLD_NAME = 0x00000004
FILE_ACTION_RENAMED_NEW_NAME = 0x00000005

INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

kernel32 = ctypes.windll.kernel32

kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
]

kernel32.ReadDirectoryChangesW.restype = wintypes.BOOL
kernel32.ReadDirectoryChangesW.argtypes = [
    wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, wintypes.BOOL,
    wintypes.DWORD, wintypes.LPDWORD, wintypes.LPVOID, wintypes.LPVOID,
]

kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class FILE_NOTIFY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('NextEntryOffset', wintypes.DWORD),
        ('Action', wintypes.DWORD),
        ('FileNameLength', wintypes.DWORD),
        ('FileName', wintypes.WCHAR * 1),
    ]


def _open_dir_handle(path):
    handle = kernel32.CreateFileW(
        path,
        FILE_LIST_DIRECTORY,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OVERLAPPED,
        None,
    )
    return handle


def _read_changes(handle, buf_size=65536):
    buf = ctypes.create_string_buffer(buf_size)
    bytes_returned = wintypes.DWORD()
    success = kernel32.ReadDirectoryChangesW(
        handle,
        buf,
        buf_size,
        True,
        FILE_ACTION_ADDED | FILE_ACTION_REMOVED | FILE_ACTION_MODIFIED |
        FILE_ACTION_RENAMED_OLD_NAME | FILE_ACTION_RENAMED_NEW_NAME,
        ctypes.byref(bytes_returned),
        None,
        None,
    )
    if not success:
        return []
    events = []
    offset = 0
    while True:
        fni = FILE_NOTIFY_INFORMATION.from_buffer(buf, offset)
        name = ctypes.wstring_at(
            ctypes.addressof(fni.FileName),
            fni.FileNameLength // ctypes.sizeof(wintypes.WCHAR),
        )
        events.append((fni.Action, name))
        if fni.NextEntryOffset == 0:
            break
        offset += fni.NextEntryOffset
    return events


class DirectoryWatcher:
    """Watches a directory tree for changes using ReadDirectoryChangesW.

    This is the Win32 equivalent of subscribing to a file system change
    journal.  Each watched directory gets its own handle and thread.
    """

    def __init__(self, on_added=None, on_removed=None, on_modified=None):
        self._on_added = on_added or (lambda p: None)
        self._on_removed = on_removed or (lambda p: None)
        self._on_modified = on_modified or (lambda p: None)
        self._handles = {}
        self._threads = []
        self._running = False

    def watch(self, path):
        path = os.path.abspath(path)
        if path in self._handles:
            return
        handle = _open_dir_handle(path)
        if handle == INVALID_HANDLE_VALUE:
            raise OSError(f'Cannot watch: {path}')
        self._handles[path] = handle

    def start(self):
        self._running = True
        for path, handle in self._handles.items():
            t = threading.Thread(
                target=self._watch_loop,
                args=(path, handle),
                daemon=True,
            )
            t.start()
            self._threads.append(t)

    def stop(self):
        self._running = False
        for handle in self._handles.values():
            kernel32.CloseHandle(handle)
        self._handles.clear()

    def _watch_loop(self, root, handle):
        while self._running:
            try:
                events = _read_changes(handle)
                for action, name in events:
                    full = os.path.join(root, name)
                    if action == FILE_ACTION_ADDED:
                        self._on_added(full)
                    elif action == FILE_ACTION_REMOVED:
                        self._on_removed(full)
                    elif action == FILE_ACTION_MODIFIED:
                        self._on_modified(full)
                    elif action == FILE_ACTION_RENAMED_OLD_NAME:
                        self._on_removed(full)
                    elif action == FILE_ACTION_RENAMED_NEW_NAME:
                        self._on_added(full)
            except Exception:
                break
