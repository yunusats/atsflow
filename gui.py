import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import core

BG = "#171a23"
PANEL = "#1e222e"
FG = "#e6e9f0"
MUTED = "#8b93a7"
ACCENT = "#4f8cff"


class App:
    def __init__(self, root, discovery, server, shared_dir, url):
        self.discovery = discovery
        self.server = server
        self.shared_dir = shared_dir
        self.url = url

        root.title("iMesh NG")
        root.geometry("480x440")
        root.configure(bg=BG)
        root.minsize(420, 380)

        tk.Label(
            root, text="AtsFlow", font=("Segoe UI", 16, "bold"),
            bg=BG, fg=ACCENT,
        ).pack(pady=(14, 2))
        tk.Label(
            root, text="Yerel Ag Muzik & Dosya Akisi", font=("Segoe UI", 9),
            bg=BG, fg=MUTED,
        ).pack()

        info = tk.Frame(root, bg=PANEL)
        info.pack(fill="x", padx=14, pady=12)
        info.grid_columnconfigure(1, weight=1)
        self._row(info, 0, "Bilgisayar:", discovery.name)
        self._row(info, 1, "Web arayuzu:", url)
        self.dir_label = self._row(info, 2, "Paylasim klasoru:", shared_dir)

        btns = tk.Frame(root, bg=BG)
        btns.pack(fill="x", padx=14)
        tk.Button(
            btns, text="Klasor Degistir", command=self.change_folder,
            bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=FG,
            relief="flat", padx=10, pady=4, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            btns, text="Web Arayuzunu Ac", command=self.open_browser,
            bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=FG,
            relief="flat", padx=10, pady=4, cursor="hand2",
        ).pack(side="left", padx=8)

        tk.Label(
            root, text="AGDEKI BILGISAYARLAR", font=("Segoe UI", 9, "bold"),
            bg=BG, fg=MUTED, anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 4))

        self.listbox = tk.Listbox(
            root, bg=PANEL, fg=FG, relief="flat",
            selectbackground=ACCENT, font=("Consolas", 10),
        )
        self.listbox.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.schedule_refresh()

    def _row(self, parent, r, label, value):
        tk.Label(parent, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=10, pady=5
        )
        val = tk.Label(parent, text=value, bg=PANEL, fg=FG, font=("Segoe UI", 9, "bold"))
        val.grid(row=r, column=1, sticky="w", padx=4, pady=5)
        return val

    def refresh_list(self):
        self.listbox.delete(0, "end")
        peers = self.discovery.get_peers()
        if not peers:
            self.listbox.insert("end", "  (agda baska bilgisayar bulunamadi)")
        for p in peers:
            self.listbox.insert("end", f"  {p['name']}  -  {p['ip']}:{p['port']}")

    def schedule_refresh(self):
        self.refresh_list()
        self.listbox.after(4000, self.schedule_refresh)

    def change_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.shared_dir)
        if not chosen:
            return
        core.Handler.shared_dir = chosen
        self.shared_dir = chosen
        self.dir_label.config(text=chosen)
        messagebox.showinfo("AtsFlow", f"Paylasim klasoru degistirildi:\n{chosen}")

    def open_browser(self):
        import webbrowser

        webbrowser.open(self.url)


def run(discovery, server, shared_dir, url, assets_dir=None):
    root = tk.Tk()
    root.title("AtsFlow")
    if assets_dir:
        icon = os.path.join(assets_dir, "icon.ico")
        if os.path.isfile(icon):
            root.iconbitmap(icon)
    App(root, discovery, server, shared_dir, url)

    def on_close():
        discovery.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
