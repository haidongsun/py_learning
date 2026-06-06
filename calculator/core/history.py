import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'history.json')


@dataclass
class HistoryEntry:
    expression: str
    result: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


class HistoryStore:
    def __init__(self, max_entries: int = 100):
        self._entries: List[HistoryEntry] = []
        self._max_entries = max_entries
        self.load()

    @property
    def entries(self) -> List[HistoryEntry]:
        return list(self._entries)

    def add(self, expression: str, result: str):
        entry = HistoryEntry(expression=expression, result=result)
        self._entries.insert(0, entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[:self._max_entries]
        self.save()

    def clear(self):
        self._entries.clear()
        self.save()

    def save(self):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump([asdict(e) for e in self._entries], f, ensure_ascii=False, indent=2)
        except (IOError, OSError):
            pass

    def load(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._entries = [HistoryEntry(**item) for item in data]
        except (IOError, OSError, json.JSONDecodeError):
            self._entries = []
