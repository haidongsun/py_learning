"""Entry point for the calculator desktop application.

Run with: python -m calculator.app
"""

import tkinter as tk
from calculator.gui.main_window import CalculatorApp


def main():
    root = tk.Tk()
    CalculatorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
