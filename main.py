# pharmacy-system/main.py
import tkinter as tk
from tkinter import ttk, messagebox
from medicine import add_medicine, get_all_medicines, get_medicine_by_id, update_medicine, delete_medicine

# ─── Color Palette ───────────────────────────────────────────────
BG        = "#0F1117"
PANEL     = "#1A1D27"
ACCENT    = "#00C2A8"
ACCENT_DK = "#009E88"
DANGER    = "#E05C5C"
TEXT      = "#E8EAF0"
MUTED     = "#6B7280"
BORDER    = "#2A2D3A"
ROW_ODD   = "#1E2130"
ROW_EVEN  = "#1A1D27"

FONT_HEAD  = ("Segoe UI", 22, "bold")
FONT_SUB   = ("Segoe UI", 11)
FONT_LABEL = ("Segoe UI", 10, "bold")
FONT_INPUT = ("Segoe UI", 10)
FONT_BTN   = ("Segoe UI", 10, "bold")
FONT_TABLE = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)


def styled_button(parent, text, command, color=ACCENT, fg=BG, width=14):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=color, fg=fg, font=FONT_BTN,
        relief="flat", bd=0, cursor="hand2",
        padx=12, pady=6, width=width,
        activebackground=ACCENT_DK, activeforeground=BG
    )
    return btn


def labeled_entry(parent, label_text, row, show=None):
    tk.Label(parent, text=label_text, bg=PANEL, fg=TEXT,
             font=FONT_LABEL).grid(row=row, column=0, sticky="w", pady=(8, 2))
    var = tk.StringVar()
    e = tk.Entry(parent, textvariable=var, font=FONT_INPUT,
                 bg="#262A38", fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0, highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT,
                 show=show if show else "")
    e.grid(row=row, column=1, sticky="ew", pady=(8, 2), padx=(12, 0), ipady=6)
    return var


# ─── Medicine CRUD Screen ──────────────────────────────────────────
class MedicineFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller
        self._selected_id = None
        self._all_data = []
        self._build_ui()

    def on_show(self):
        self.refresh_table()

    # ── Layout skeleton ──────────────────────────────────────────
    def _build_ui(self):
        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x", side="top")

        left_col = tk.Frame(header, bg=PANEL)
        left_col.pack(side="left", padx=20, pady=10, anchor="w")

        title_row = tk.Frame(left_col, bg=PANEL)
        title_row.pack(anchor="w")
        tk.Label(title_row, text="💊", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 20)).pack(side="left", padx=(0, 6))
        tk.Label(title_row, text="Pharmacy Management", bg=PANEL, fg=TEXT,
                 font=FONT_HEAD).pack(side="left")

        back_link = tk.Label(left_col, text="← Dashboard", bg=PANEL, fg=ACCENT,
                              font=FONT_SUB, cursor="hand2")
        back_link.pack(anchor="w", pady=(2, 0))
        back_link.bind("<Button-1>", lambda _e: self.controller.show_frame("DashboardFrame"))

        tk.Label(header, text="Medicine Inventory", bg=PANEL, fg=MUTED,
                 font=FONT_SUB).pack(side="right", padx=24, pady=12)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_main(body)

    # ── Sidebar (form) ───────────────────────────────────────────
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=PANEL, width=300)
        sidebar.pack(side="left", fill="y", padx=(12, 6), pady=12)
        sidebar.pack_propagate(False)

        title_row = tk.Frame(sidebar, bg=PANEL)
        title_row.pack(fill="x", padx=18, pady=(18, 4))
        self._form_title = tk.Label(title_row, text="Add Medicine",
                                    bg=PANEL, fg=ACCENT, font=("Segoe UI", 13, "bold"))
        self._form_title.pack(side="left")

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=18, pady=(0, 8))

        form = tk.Frame(sidebar, bg=PANEL)
        form.pack(fill="x", padx=18)
        form.columnconfigure(1, weight=1)

        self._var_name    = labeled_entry(form, "Medicine Name",   0)
        self._var_price   = labeled_entry(form, "Price (৳)",        1)
        self._var_stock   = labeled_entry(form, "Stock (units)",    2)
        self._var_expires = labeled_entry(form, "Expiry Date",      3)

        tk.Label(form, text="Format: YYYY-MM-DD", bg=PANEL, fg=MUTED,
                 font=FONT_SMALL).grid(row=4, column=1, sticky="w", padx=(12, 0))

        btn_frame = tk.Frame(sidebar, bg=PANEL)
        btn_frame.pack(fill="x", padx=18, pady=(18, 0))

        self._btn_save = styled_button(btn_frame, "➕  Add", self._on_save, width=12)
        self._btn_save.pack(fill="x", pady=(0, 6))

        self._btn_update = styled_button(btn_frame, "✏️  Update", self._on_update,
                                         color="#3B82F6", fg=TEXT, width=12)
        self._btn_update.pack(fill="x", pady=(0, 6))
        self._btn_update.config(state="disabled")

        self._btn_delete = styled_button(btn_frame, "🗑  Delete", self._on_delete,
                                         color=DANGER, fg=TEXT, width=12)
        self._btn_delete.pack(fill="x", pady=(0, 6))
        self._btn_delete.config(state="disabled")

        self._btn_clear = styled_button(btn_frame, "✖  Clear", self._clear_form,
                                        color=BORDER, fg=MUTED, width=12)
        self._btn_clear.pack(fill="x")

        self._status = tk.Label(sidebar, text="", bg=PANEL, fg=ACCENT,
                                font=FONT_SMALL, wraplength=260, justify="left")
        self._status.pack(fill="x", padx=18, pady=(12, 0))

        self._stats_frame = tk.Frame(sidebar, bg=BG, bd=0)
        self._stats_frame.pack(fill="x", padx=18, pady=(16, 18), side="bottom")
        self._lbl_total   = self._stat_label("Total medicines", "—")
        self._lbl_low     = self._stat_label("Low stock (< 10)", "—")

    def _stat_label(self, title, value):
        row = tk.Frame(self._stats_frame, bg=BG)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=title, bg=BG, fg=MUTED, font=FONT_SMALL).pack(side="left")
        lbl = tk.Label(row, text=value, bg=BG, fg=ACCENT, font=("Segoe UI", 10, "bold"))
        lbl.pack(side="right")
        return lbl

    # ── Main table area ──────────────────────────────────────────
    def _build_main(self, parent):
        main = tk.Frame(parent, bg=BG)
        main.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=12)

        search_row = tk.Frame(main, bg=BG)
        search_row.pack(fill="x", pady=(0, 8))
        tk.Label(search_row, text="🔍", bg=BG, fg=MUTED,
                 font=("Segoe UI", 12)).pack(side="left", padx=(4, 4))

        PLACEHOLDER = "Search by name..."
        self._search_var = tk.StringVar()
        self._search_var.trace("w", lambda *_: self._filter_table())

        search = tk.Entry(search_row, textvariable=self._search_var,
                          font=FONT_INPUT, bg=PANEL, fg=MUTED,
                          insertbackground=ACCENT, relief="flat",
                          highlightthickness=1, highlightbackground=BORDER,
                          highlightcolor=ACCENT)
        search.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))

        def _show_placeholder():
            search.insert(0, PLACEHOLDER)
            search.config(fg=MUTED)

        def _on_focus_in(_e):
            if search.get() == PLACEHOLDER:
                search.delete(0, "end")
                search.config(fg=TEXT)

        def _on_focus_out(_e):
            if search.get() == "":
                _show_placeholder()

        search.bind("<FocusIn>", _on_focus_in)
        search.bind("<FocusOut>", _on_focus_out)
        _show_placeholder()

        styled_button(search_row, "🔄 Refresh", self.refresh_table,
                      color=BORDER, fg=TEXT, width=10).pack(side="right")

        cols = ("ID", "Name", "Price (৳)", "Stock", "Expiry Date")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Pharmacy.Treeview",
                        background=ROW_EVEN, fieldbackground=ROW_EVEN,
                        foreground=TEXT, font=FONT_TABLE,
                        rowheight=34, borderwidth=0)
        style.configure("Pharmacy.Treeview.Heading",
                        background=PANEL, foreground=ACCENT,
                        font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Pharmacy.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        frame_tree = tk.Frame(main, bg=BG)
        frame_tree.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(frame_tree, columns=cols, show="headings",
                                  style="Pharmacy.Treeview", selectmode="browse")

        col_widths = {"ID": 52, "Name": 220, "Price (৳)": 110, "Stock": 90, "Expiry Date": 120}
        for c in cols:
            self._tree.heading(c, text=c, anchor="center")
            self._tree.column(c, width=col_widths[c], anchor="center")

        self._tree.tag_configure("odd",  background=ROW_ODD)
        self._tree.tag_configure("even", background=ROW_EVEN)
        self._tree.tag_configure("low",  foreground=DANGER)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)

        del_row = tk.Frame(main, bg=BG)
        del_row.pack(fill="x", pady=(8, 0))
        styled_button(del_row, "🗑  Delete Selected", self._on_delete,
                      color=DANGER, fg=TEXT, width=18).pack(side="right")
        self._lbl_row_count = tk.Label(del_row, text="", bg=BG, fg=MUTED, font=FONT_SMALL)
        self._lbl_row_count.pack(side="left")

    # ── CRUD handlers ────────────────────────────────────────────
    def _fields(self):
        return (self._var_name.get().strip(),
                self._var_price.get().strip(),
                self._var_stock.get().strip(),
                self._var_expires.get().strip())

    def _validate(self, name, price, stock, expires):
        if not all([name, price, stock, expires]):
            messagebox.showwarning("Missing Fields", "Please fill in all fields.")
            return False
        try:
            float(price)
        except ValueError:
            messagebox.showerror("Invalid Price", "Price must be a number.")
            return False
        try:
            int(stock)
        except ValueError:
            messagebox.showerror("Invalid Stock", "Stock must be a whole number.")
            return False
        if len(expires) != 10 or expires[4] != "-" or expires[7] != "-":
            messagebox.showerror("Invalid Date", "Use YYYY-MM-DD format.")
            return False
        return True

    def _on_save(self):
        name, price, stock, expires = self._fields()
        if not self._validate(name, price, stock, expires):
            return
        try:
            add_medicine(name, float(price), int(stock), expires)
            self._set_status(f"✅ '{name}' added successfully.")
            self._clear_form()
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_update(self):
        if not self._selected_id:
            messagebox.showinfo("No Selection", "Select a row to update.")
            return
        name, price, stock, expires = self._fields()
        if not self._validate(name, price, stock, expires):
            return
        try:
            update_medicine(self._selected_id, name, float(price), int(stock), expires)
            self._set_status(f"✅ Medicine ID {self._selected_id} updated.")
            self._clear_form()
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_delete(self):
        if not self._selected_id:
            messagebox.showinfo("No Selection", "Select a row to delete.")
            return
        med = get_medicine_by_id(self._selected_id)
        name = med["name"] if med else f"ID {self._selected_id}"
        confirm = messagebox.askyesno("Confirm Delete",
                                      f"Delete '{name}'?\nThis cannot be undone.")
        if not confirm:
            return
        try:
            delete_medicine(self._selected_id)
            self._set_status(f"🗑 '{name}' deleted.")
            self._clear_form()
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_row_select(self, _event):
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        self._selected_id = int(values[0])
        self._var_name.set(values[1])
        self._var_price.set(values[2])
        self._var_stock.set(values[3])
        self._var_expires.set(values[4])
        self._form_title.config(text=f"Edit  ·  ID {self._selected_id}")
        self._btn_update.config(state="normal")
        self._btn_delete.config(state="normal")
        self._btn_save.config(state="disabled")

    # ── Table helpers ────────────────────────────────────────────
    def refresh_table(self):
        self._all_data = get_all_medicines()
        self._render_rows(self._all_data)
        self._update_stats(self._all_data)

    def _filter_table(self):
        q = self._search_var.get().lower()
        filtered = [r for r in self._all_data if q in r["name"].lower()]
        self._render_rows(filtered)

    def _render_rows(self, rows):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, r in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            tags = (tag, "low") if r["stock"] < 10 else (tag,)
            self._tree.insert("", "end", values=(
                r["id"], r["name"],
                f"{float(r['price']):.2f}",
                r["stock"], r["expires_date"]
            ), tags=tags)
        count = len(rows)
        self._lbl_row_count.config(text=f"{count} medicine{'s' if count != 1 else ''} shown")

    def _update_stats(self, rows):
        low = sum(1 for r in rows if r["stock"] < 10)
        self._lbl_total.config(text=str(len(rows)))
        self._lbl_low.config(text=str(low), fg=DANGER if low else ACCENT)

    # ── Form utils ───────────────────────────────────────────────
    def _clear_form(self):
        for v in (self._var_name, self._var_price, self._var_stock, self._var_expires):
            v.set("")
        self._selected_id = None
        self._form_title.config(text="Add Medicine")
        self._btn_update.config(state="disabled")
        self._btn_delete.config(state="disabled")
        self._btn_save.config(state="normal")
        self._tree.selection_remove(self._tree.selection())
        self._set_status("")

    def _set_status(self, msg):
        self._status.config(text=msg)
        if msg:
            self.after(4000, lambda: self._status.config(text=""))