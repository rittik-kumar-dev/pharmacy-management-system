# pharmacy-system/login.py
import tkinter as tk
from tkinter import messagebox
from auth import admin_exists, create_admin, verify_admin

BG        = "#0F1117"
PANEL     = "#1A1D27"
ACCENT    = "#00C2A8"
ACCENT_DK = "#009E88"
DANGER    = "#E05C5C"
TEXT      = "#E8EAF0"
MUTED     = "#6B7280"
BORDER    = "#2A2D3A"

FONT_HEAD  = ("Segoe UI", 20, "bold")
FONT_SUB   = ("Segoe UI", 10)
FONT_LABEL = ("Segoe UI", 10, "bold")
FONT_INPUT = ("Segoe UI", 11)
FONT_BTN   = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 9)


def styled_button(parent, text, command, color=ACCENT, fg=BG):
    return tk.Button(
        parent, text=text, command=command,
        bg=color, fg=fg, font=FONT_BTN,
        relief="flat", bd=0, cursor="hand2",
        padx=12, pady=8, activebackground=ACCENT_DK, activeforeground=BG
    )


def labeled_entry(parent, label_text, show=None):
    tk.Label(parent, text=label_text, bg=PANEL, fg=TEXT,
              font=FONT_LABEL).pack(anchor="w", pady=(10, 2))
    var = tk.StringVar()
    e = tk.Entry(parent, textvariable=var, font=FONT_INPUT,
                 bg="#262A38", fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0, highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT,
                 show=show if show else "")
    e.pack(fill="x", ipady=8)
    return var, e


class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller

        self._card = tk.Frame(self, bg=PANEL)
        self._card.pack(expand=True, fill="both", padx=30, pady=40)

    def on_show(self):
        self._clear_card()
        if admin_exists():
            self._build_login_view()
        else:
            self._build_register_view()

    def _header(self, title, subtitle):
        tk.Label(self._card, text="💊", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 26)).pack(pady=(30, 0))
        tk.Label(self._card, text=title, bg=PANEL, fg=TEXT,
                 font=FONT_HEAD).pack(pady=(6, 0))
        tk.Label(self._card, text=subtitle, bg=PANEL, fg=MUTED,
                 font=FONT_SUB).pack(pady=(2, 10))

    def _clear_card(self):
        for widget in self._card.winfo_children():
            widget.destroy()

    def _build_login_view(self):
        self._clear_card()
        self._header("Admin Login", "Sign in to manage the pharmacy")

        form = tk.Frame(self._card, bg=PANEL)
        form.pack(fill="x", padx=30)

        self._user_var, _ = labeled_entry(form, "Username")
        self._pass_var, pass_entry = labeled_entry(form, "Password", show="*")
        pass_entry.bind("<Return>", lambda _e: self._on_login())

        self._status = tk.Label(self._card, text="", bg=PANEL, fg=DANGER,
                                 font=FONT_SMALL, wraplength=300)
        self._status.pack(pady=(10, 0))
        styled_button(self._card, "Login", self._on_login).pack(
            fill="x", padx=30, pady=(14, 4))

        create_link = tk.Label(self._card, text="+ Create new admin",
                                bg=PANEL, fg=ACCENT, font=FONT_SMALL, cursor="hand2")
        create_link.pack(pady=(10, 0))
        create_link.bind("<Button-1>", lambda _e: self._build_register_view())

    def _on_login(self):
        username = self._user_var.get()
        password = self._pass_var.get()

        if not username or not password:
            self._status.config(text="Please enter both username and password.")
            return

        if verify_admin(username, password):
            self.controller.admin_username = username
            self.controller.show_frame("DashboardFrame")
        else:
            self._status.config(text="Invalid username or password.")
            self._pass_var.set("")

    def _build_register_view(self):
        self._clear_card()
        self._header("Create Admin Account", "No admin exists yet — set one up now")

        form = tk.Frame(self._card, bg=PANEL)
        form.pack(fill="x", padx=30)

        self._new_user_var, _ = labeled_entry(form, "Username")
        self._new_pass_var, _ = labeled_entry(form, "Password", show="*")
        self._confirm_var, confirm_entry = labeled_entry(form, "Confirm Password", show="*")
        confirm_entry.bind("<Return>", lambda _e: self._on_register())

        self._status = tk.Label(self._card, text="", bg=PANEL, fg=DANGER,
                                 font=FONT_SMALL, wraplength=300)
        self._status.pack(pady=(10, 0))
        styled_button(self._card, "Create Account", self._on_register).pack(
            fill="x", padx=30, pady=(14, 4))

        back_link = tk.Label(self._card, text="← Back to login",
                              bg=PANEL, fg=MUTED, font=FONT_SMALL, cursor="hand2")
        back_link.pack(pady=(10, 0))
        back_link.bind("<Button-1>", lambda _e: self._build_login_view())

    def _on_register(self):
        username = self._new_user_var.get().strip()
        password = self._new_pass_var.get()
        confirm  = self._confirm_var.get()

        if not username or not password:
            self._status.config(text="Username and password cannot be empty.")
            return
        if len(password) < 6:
            self._status.config(text="Password must be at least 6 characters.")
            return
        if password != confirm:
            self._status.config(text="Passwords do not match.")
            return

        try:
            create_admin(username, password)
            messagebox.showinfo("Account Created",
                                 f"Admin '{username}' created. Please log in.")
            self._build_login_view()
        except ValueError as e:
            self._status.config(text=str(e))