import tkinter as tk
from translator_gui import TranslatorGUI
from translator_core import PortTranslatorCore

if __name__ == "__main__":
    root = tk.Tk()
    core = PortTranslatorCore()
    app = TranslatorGUI(root, core)
    root.mainloop()