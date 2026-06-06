from tkinter import ttk
from typing import Dict, List, Callable

LIGHT_THEME = {
    'name': 'Light',
    'bg': '#F2F2F7',
    'toolbar_bg': '#F2F2F7',
    'display_bg': '#FFFFFF',
    'display_fg': '#1C1C1E',
    'display_expr_fg': '#8E8E93',
    'display_border': '#D1D1D6',
    'number_bg': '#FFFFFF',
    'number_fg': '#1C1C1E',
    'number_active_bg': '#E5E5EA',
    'operator_bg': '#FF9F0A',
    'operator_fg': '#FFFFFF',
    'operator_active_bg': '#FFB340',
    'sci_bg': '#E5E5EA',
    'sci_fg': '#1C1C1E',
    'sci_active_bg': '#D1D1D6',
    'equal_bg': '#007AFF',
    'equal_fg': '#FFFFFF',
    'equal_active_bg': '#3399FF',
    'clear_bg': '#E5E5EA',
    'clear_fg': '#1C1C1E',
    'clear_active_bg': '#D1D1D6',
    'paren_bg': '#E5E5EA',
    'paren_fg': '#1C1C1E',
    'paren_active_bg': '#D1D1D6',
}

DARK_THEME = {
    'name': 'Dark',
    'bg': '#000000',
    'toolbar_bg': '#000000',
    'display_bg': '#1C1C1E',
    'display_fg': '#FFFFFF',
    'display_expr_fg': '#8E8E93',
    'display_border': '#38383A',
    'number_bg': '#333333',
    'number_fg': '#FFFFFF',
    'number_active_bg': '#444444',
    'operator_bg': '#FF9F0A',
    'operator_fg': '#FFFFFF',
    'operator_active_bg': '#FFB340',
    'sci_bg': '#A5A5A6',
    'sci_fg': '#000000',
    'sci_active_bg': '#C0C0C0',
    'equal_bg': '#FF9F0A',
    'equal_fg': '#FFFFFF',
    'equal_active_bg': '#FFB340',
    'clear_bg': '#A5A5A6',
    'clear_fg': '#000000',
    'clear_active_bg': '#C0C0C0',
    'paren_bg': '#333333',
    'paren_fg': '#FFFFFF',
    'paren_active_bg': '#444444',
}


class ThemeManager:
    def __init__(self):
        self._current = LIGHT_THEME
        self._is_dark = False
        self._listeners: List[Callable] = []

    @property
    def theme(self) -> Dict:
        return self._current

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    def toggle(self):
        self._is_dark = not self._is_dark
        self._current = DARK_THEME if self._is_dark else LIGHT_THEME
        self._notify()

    def subscribe(self, callback: Callable):
        self._listeners.append(callback)

    def _notify(self):
        for cb in self._listeners:
            cb(self._current)
