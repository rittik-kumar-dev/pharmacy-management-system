# Run this file: one root, a full-window login, and a persistent application shell.
import tkinter as tk

BG = "#0F1117"
PANEL = "#1A1D27"
TEXT = "#E8EAF0"
MUTED = "#6B7280"
ACCENT = "#00C2A8"
DANGER = "#E05C5C"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Medicine Shop Management System")
        self.geometry("1280x720+80+60")
        self.minsize(1100, 680)
        self.configure(bg=BG)
        self.admin_username = None
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        self._build_shell()
        self._init_frames()
        self.show_frame("LoginFrame")

    def _build_shell(self):
        self.shell = tk.Frame(self.container, bg=BG)
        self.shell.grid(row=0, column=0, sticky="nsew")
        header = tk.Frame(self.shell, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 12))
        tk.Label(header, text="Medicine Shop Management System", bg=BG, fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(side="left")
        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        self._username_lbl = tk.Label(right, bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self._username_lbl.pack(anchor="e")
        tk.Button(right, text="Logout", command=self.logout, bg=BG, fg=DANGER,
                  activebackground=PANEL, activeforeground=DANGER,
                  relief="flat", bd=0, cursor="hand2").pack(anchor="e")

        body = tk.Frame(self.shell, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        sidebar = tk.Frame(body, bg=PANEL, width=160)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)
        self._nav_buttons = {}
        for label, page in (("Dashboard", "DashboardFrame"), ("Medicines", "MedicineFrame"),
                            ("Sales", "SalesFrame"), ("Suppliers", "SupplierFrame"), ("Reports", None)):
            button = tk.Button(sidebar, text=label, anchor="w", padx=16, pady=12,
                               bg=PANEL, fg=TEXT if page else MUTED, relief="flat", bd=0,
                               font=("Segoe UI", 11), activebackground="#26333A",
                               activeforeground=ACCENT, cursor="hand2" if page else "arrow",
                               state="normal" if page else "disabled", disabledforeground=MUTED,
                               command=lambda name=page: self.show_frame(name))
            button.pack(fill="x")
            if page:
                self._nav_buttons[page] = button
        self.content = tk.Frame(body, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    def _init_frames(self):
        from login import LoginFrame
        from dashboard import DashboardFrame
        from main import MedicineFrame
        from suppliers import SupplierFrame
        from sales import SalesFrame

        for screen in (LoginFrame, DashboardFrame, MedicineFrame, SupplierFrame, SalesFrame):
            parent = self.container if screen is LoginFrame else self.content
            frame = screen(parent=parent, controller=self)
            self.frames[screen.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, name):
        """Reuse the existing frames; only module content changes during navigation."""
        if name != "LoginFrame" and not self.admin_username:
            name = "LoginFrame"
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        if name == "LoginFrame":
            frame.tkraise()
        else:
            self._username_lbl.config(text=f"Logged in as: {self.admin_username}")
            for page, button in self._nav_buttons.items():
                active = page == name
                button.config(bg="#26333A" if active else PANEL,
                              fg=ACCENT if active else TEXT,
                              font=("Segoe UI", 11, "bold" if active else "normal"))
            frame.tkraise()
            self.shell.tkraise()

    def logout(self):
        self.admin_username = None
        self._username_lbl.config(text="")
        self.frames["MedicineFrame"]._clear_form()
        self.frames["SupplierFrame"]._clear_form()
        self.frames["SalesFrame"].clear_cart()
        self.show_frame("LoginFrame")


if __name__ == "__main__":
    App().mainloop()
