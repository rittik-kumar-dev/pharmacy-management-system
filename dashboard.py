# pharmacy-system/dashboard.py
import tkinter as tk
from tkinter import messagebox
from datetime import date, timedelta
from medicine import get_all_medicines

BG        = "#0F1117"
PANEL     = "#1A1D27"
ACCENT    = "#00C2A8"
ACCENT_DK = "#009E88"
DANGER    = "#E05C5C"
TEXT      = "#E8EAF0"
MUTED     = "#6B7280"
BORDER    = "#2A2D3A"
ROW_ODD   = "#1E2130"

FONT_HEAD   = ("Segoe UI", 22, "bold")
FONT_NAV    = ("Segoe UI", 11)
FONT_NAV_B  = ("Segoe UI", 11, "bold")
FONT_CARD_N = ("Segoe UI", 28, "bold")
FONT_CARD_L = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)

LOW_STOCK_THRESHOLD = 10
EXPIRING_DAYS       = 30


class DashboardFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller

        self._build_header()
        self._build_body()

    def on_show(self):
        self._username_lbl.config(
            text=f"Logged in as: {self.controller.admin_username or 'Admin'}")
        self._load_stats()

    def _build_header(self):
        header = tk.Frame(self, bg=BG, height=70)
        header.pack(fill="x", padx=20, pady=(16, 4))

        tk.Label(header, text="💊", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 22)).pack(side="left", padx=(4, 10))
        tk.Label(header, text="Pharmacy Management", bg=BG, fg=TEXT,
                 font=FONT_HEAD).pack(side="left")

        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        self._username_lbl = tk.Label(right, text="Logged in as: Admin",
                                       bg=BG, fg=MUTED, font=FONT_SMALL)
        self._username_lbl.pack(anchor="e")

        logout_link = tk.Label(right, text="Logout", bg=BG, fg=DANGER,
                                font=FONT_SMALL, cursor="hand2")
        logout_link.pack(anchor="e", pady=(4, 0))
        logout_link.bind("<Button-1>", lambda _e: self.controller.logout())

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(8, 20))

        sidebar = tk.Frame(body, bg=PANEL, width=200)
        sidebar.pack(side="left", fill="y", padx=(0, 16))
        sidebar.pack_propagate(False)

        nav_items = [
            ("Dashboard", True,  None),
            ("Medicines", True,  self._open_medicines),
            ("Sales",     False, None),
            ("Suppliers", False, None),
            ("Reports",   False, None),
        ]

        for label, enabled, command in nav_items:
            fg = TEXT if enabled else MUTED
            font = FONT_NAV_B if label == "Dashboard" else FONT_NAV
            btn = tk.Label(sidebar, text=label, bg=PANEL, fg=fg, font=font,
                           anchor="w", padx=20, pady=12,
                           cursor="hand2" if enabled else "arrow")
            btn.pack(fill="x")
            if enabled and command:
                btn.bind("<Button-1>", lambda _e, c=command: c())
            elif not enabled:
                btn.bind("<Button-1>",
                         lambda _e, l=label: messagebox.showinfo(
                             l, f"{l} module is coming soon."))

        self._content = tk.Frame(body, bg=BG)
        self._content.pack(side="left", fill="both", expand=True)

        tk.Label(self._content, text="Dashboard", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 16))

        self._cards_row = tk.Frame(self._content, bg=BG)
        self._cards_row.pack(fill="x", pady=(0, 20))

        self._card_medicines = self._make_card(self._cards_row, "Medicines", "—")
        self._card_low_stock = self._make_card(self._cards_row, "Low Stock", "—", color=DANGER)
        self._card_expiring  = self._make_card(self._cards_row, "Expiring Soon", "—", color="#E0A75C")

        tk.Label(self._content, text="Recently Added Medicines", bg=BG, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(4, 8))

        self._recent_frame = tk.Frame(self._content, bg=PANEL)
        self._recent_frame.pack(fill="both", expand=True)

    def _make_card(self, parent, label, value, color=ACCENT):
        card = tk.Frame(parent, bg=PANEL, padx=24, pady=18)
        card.pack(side="left", padx=(0, 14))

        num_lbl = tk.Label(card, text=value, bg=PANEL, fg=color, font=FONT_CARD_N)
        num_lbl.pack()
        tk.Label(card, text=label, bg=PANEL, fg=MUTED, font=FONT_CARD_L).pack()

        card.num_label = num_lbl
        return card

    def _load_stats(self):
        try:
            meds = get_all_medicines()
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not load stats:\n{e}")
            return

        total = len(meds)
        low_stock = [m for m in meds if m["stock"] < LOW_STOCK_THRESHOLD]
        cutoff = date.today() + timedelta(days=EXPIRING_DAYS)
        expiring = [m for m in meds if m["expires_date"] and m["expires_date"] <= cutoff]

        self._card_medicines.num_label.config(text=str(total))
        self._card_low_stock.num_label.config(text=str(len(low_stock)))
        self._card_expiring.num_label.config(text=str(len(expiring)))

        recent = sorted(meds, key=lambda m: m["id"], reverse=True)[:5]
        for widget in self._recent_frame.winfo_children():
            widget.destroy()

        if not recent:
            tk.Label(self._recent_frame, text="No medicines added yet.",
                     bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(pady=20)
        else:
            for i, m in enumerate(recent):
                row_bg = ROW_ODD if i % 2 else PANEL
                row = tk.Frame(self._recent_frame, bg=row_bg)
                row.pack(fill="x")
                tk.Label(row, text=m["name"], bg=row_bg, fg=TEXT,
                         font=FONT_NAV, anchor="w", width=25, padx=16, pady=8
                         ).pack(side="left")
                tk.Label(row, text=f"Stock: {m['stock']}", bg=row_bg, fg=MUTED,
                         font=FONT_SMALL).pack(side="left", padx=(0, 20))
                tk.Label(row, text=f"৳{m['price']}", bg=row_bg, fg=ACCENT,
                         font=FONT_SMALL).pack(side="left")

    def _open_medicines(self):
        self.controller.show_frame("MedicineFrame")