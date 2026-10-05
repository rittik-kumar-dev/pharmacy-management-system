# Medicine Shop Management System - main.py
import tkinter as tk
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
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


def format_name(value):
    return " ".join(word.capitalize() if word.islower() else word
                    for word in (value or "").split())


def format_strength(value):
    value = " ".join((value or "").split())
    return re.sub(r"(?<=\d)\s*(mcg|mg|g|ml|iu)\b",
                  lambda match: " " + match.group(1).lower(), value, flags=re.IGNORECASE)


def styled_button(parent, text, command, color=ACCENT, fg=BG, width=14):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=color, fg=fg, font=FONT_BTN,
        relief="flat", bd=0, cursor="hand2",
        padx=12, pady=6, width=width,
        activebackground=ACCENT_DK, activeforeground=BG
    )
    return btn


def labeled_entry(parent, label_text, row, show=None, compact=False):
    row_padding = (4, 1) if compact else (8, 2)
    tk.Label(parent, text=label_text, bg=PANEL, fg=TEXT,
             font=FONT_LABEL).grid(row=row, column=0, sticky="w", pady=row_padding)
    var = tk.StringVar()
    e = tk.Entry(parent, textvariable=var, font=FONT_INPUT,
                 bg="#262A38", fg=TEXT, insertbackground=ACCENT, width=1,
                 relief="flat", bd=0, highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT,
                 show=show if show else "")
    e.grid(row=row, column=1, sticky="ew", pady=row_padding, padx=(12, 0),
           ipady=3 if compact else 6)
    return var


# ─── Medicine CRUD Screen ──────────────────────────────────────────
class MedicineFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller
        self._selected_id = None
        self._all_data = []
        self._status_after_id = None
        self._build_ui()

    def on_show(self):
        self.refresh_table()

    # ── Layout skeleton ──────────────────────────────────────────
    def _build_ui(self):
        tk.Label(self, text="Medicine Inventory", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(8, 4))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_main(body)

    # ── Sidebar (form) ───────────────────────────────────────────
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=PANEL, width=280)
        sidebar.pack(side="left", fill="y", padx=(12, 6), pady=8)
        sidebar.pack_propagate(False)

        title_row = tk.Frame(sidebar, bg=PANEL)
        title_row.pack(fill="x", padx=18, pady=(8, 2))
        self._form_title = tk.Label(title_row, text="Medicine Details",
                                    bg=PANEL, fg=ACCENT, font=("Segoe UI", 13, "bold"))
        self._form_title.pack(side="left")
        self._selected_label = tk.Label(sidebar, text="", bg=PANEL, fg=MUTED, font=FONT_SMALL)
        self._selected_label.pack(fill="x", padx=18, pady=(0, 2))

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=18, pady=(0, 4))

        form = tk.Frame(sidebar, bg=PANEL)
        form.pack(fill="x", padx=18)
        form.columnconfigure(1, weight=1)

        self._var_name    = labeled_entry(form, "Medicine Name",   0, compact=True)
        self._var_generic = labeled_entry(form, "Group/Generic", 1, compact=True)
        self._var_strength = labeled_entry(form, "Strength", 2, compact=True)
        self._var_price   = labeled_entry(form, "Price (৳)",        3, compact=True)
        self._var_stock   = labeled_entry(form, "Stock Quantity",   4, compact=True)
        self._var_expires = labeled_entry(form, "Expiry Date",      5, compact=True)

        tk.Label(form, text="Format: YYYY-MM-DD", bg=PANEL, fg=MUTED,
                 font=FONT_SMALL).grid(row=6, column=1, sticky="w", padx=(12, 0))

        btn_frame = tk.Frame(sidebar, bg=PANEL)
        btn_frame.pack(fill="x", padx=18, pady=(8, 0))

        self._btn_save = styled_button(btn_frame, "➕  Add", self._on_save, width=12)
        self._btn_save.pack(fill="x", pady=(0, 3))

        self._btn_update = styled_button(btn_frame, "✏️  Update", self._on_update,
                                         color="#3B82F6", fg=TEXT, width=12)
        self._btn_update.pack(fill="x", pady=(0, 3))
        self._btn_update.config(state="disabled")

        self._btn_delete = styled_button(btn_frame, "🗑  Delete", self._on_delete,
                                         color=DANGER, fg=TEXT, width=12)
        self._btn_delete.pack(fill="x", pady=(0, 3))
        self._btn_delete.config(state="disabled")

        self._btn_clear = styled_button(btn_frame, "✖  Clear", self._clear_form,
                                        color=BORDER, fg=MUTED, width=12)
        self._btn_clear.pack(fill="x")
        for button in (self._btn_save, self._btn_update, self._btn_delete, self._btn_clear):
            button.config(pady=3)

        self._status = tk.Label(sidebar, text="", bg=PANEL, fg=ACCENT,
                                font=FONT_SMALL, wraplength=260, justify="left")
        self._status.pack(fill="x", padx=18, pady=(4, 0))

        self._stats_frame = tk.Frame(sidebar, bg=BG, bd=0)
        self._stats_frame.pack(fill="x", padx=18, pady=(4, 6), side="bottom")
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

        PLACEHOLDER = "Search by name, generic or strength..."
        self._search_placeholder = PLACEHOLDER
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


        cols = ("ID", "Medicine Name", "Group/Generic", "Strength", "Stock Quantity", "Price (৳)", "Expiry Date")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Pharmacy.Treeview",
                        background=ROW_EVEN, fieldbackground=ROW_EVEN,
                        foreground=TEXT, font=FONT_TABLE,
                        rowheight=34, borderwidth=0)
        style.configure("Pharmacy.Treeview.Heading",
                        background=PANEL, foreground=ACCENT,
                        font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Pharmacy.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        frame_tree = tk.Frame(main, bg=BG)
        frame_tree.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(frame_tree, columns=cols, show="headings",
                                  style="Pharmacy.Treeview", selectmode="browse")

        col_widths = dict(zip(cols, (40, 150, 145, 80, 105, 75, 100)))
        min_widths = dict(zip(cols, (30, 95, 95, 60, 95, 60, 90)))
        for c in cols:
            self._tree.heading(c, text=c, anchor="center")
            self._tree.column(c, width=col_widths[c], minwidth=min_widths[c],
                              anchor="w" if c in ("Medicine Name", "Group/Generic") else "center")

        def fit_columns(event):
            extra = max(0, event.width - 4 - sum(min_widths.values()))
            for c in cols:
                self._tree.column(c, width=min_widths[c] + int(extra * col_widths[c] / sum(col_widths.values())))

        self._tree.bind("<Configure>", fit_columns)

        self._tree.tag_configure("odd",  background=ROW_ODD)
        self._tree.tag_configure("even", background=ROW_EVEN)
        self._tree.tag_configure("low",  foreground=DANGER)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        frame_tree.rowconfigure(0, weight=1)
        frame_tree.columnconfigure(0, weight=1)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)

        del_row = tk.Frame(main, bg=BG)
        del_row.pack(fill="x", pady=(8, 0))
        self._lbl_row_count = tk.Label(del_row, text="", bg=BG, fg=MUTED, font=FONT_SMALL)
        self._lbl_row_count.pack(side="left")

    # ── CRUD handlers ────────────────────────────────────────────
    def _fields(self):
        return (self._var_name.get().strip(),
                self._var_price.get().strip(),
                self._var_stock.get().strip(),
                self._var_expires.get().strip())

    def _validate(self, name, price, stock, expires):
        strength = self._var_strength.get().strip()
        if not all([name, price, stock, expires, strength]):
            messagebox.showerror("Missing Fields", "Enter medicine name, strength, price, stock quantity, and expiry date.")
            return False
        if any(len(v) > 100 for v in (name, self._var_generic.get().strip(), strength)):
            messagebox.showerror("Invalid Details", "Name, generic, and strength must each be at most 100 characters.")
            return False
        try:
            amount = Decimal(price)
            if not amount.is_finite() or amount <= 0 or amount > Decimal("99999999.99"):
                raise ValueError
            if amount != amount.quantize(Decimal("0.01")):
                raise ValueError
        except (InvalidOperation, ValueError):
            messagebox.showerror("Invalid Price", "Enter a positive price with at most 2 decimal places (maximum 99999999.99).")
            return False
        if not re.fullmatch(r"[0-9]+", stock) or len(stock.lstrip("0")) > 10 or int(stock.lstrip("0") or "0") > 2147483647:
            messagebox.showerror("Invalid Stock", "Enter a non-negative whole number (maximum 2147483647).")
            return False
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", expires):
                raise ValueError
            datetime.strptime(expires, "%Y-%m-%d")
            if int(expires[:4]) < 1000:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Date", "Enter a valid date in YYYY-MM-DD format (year 1000 or later).")
            return False
        return True

    def _on_save(self):
        name, price, stock, expires = self._fields()
        if not self._validate(name, price, stock, expires):
            return
        try:
            add_medicine(format_name(name), Decimal(price), int(stock.lstrip("0") or "0"), expires,
                         format_name(self._var_generic.get()), format_strength(self._var_strength.get()))
            self._clear_form()
            self._set_status(f"✅ '{name}' added successfully.")
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
            update_medicine(self._selected_id, format_name(name), Decimal(price), int(stock.lstrip("0") or "0"), expires,
                            format_name(self._var_generic.get()), format_strength(self._var_strength.get()))
            updated_id = self._selected_id
            self._clear_form()
            self._set_status(f"✅ Medicine ID {updated_id} updated.")
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_delete(self):
        if not self._selected_id:
            messagebox.showinfo("No Selection", "Select a row to delete.")
            return
        try:
            med = get_medicine_by_id(self._selected_id)
            name = format_name(med["name"]) if med else f"ID {self._selected_id}"
            if not messagebox.askyesno("Confirm Delete", f"Delete '{name}'?\nThis cannot be undone."):
                return
            delete_medicine(self._selected_id)
            self._clear_form()
            self._set_status(f"🗑 '{name}' deleted.")
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_row_select(self, _event):
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        self._selected_id = int(values[0])
        med = next((r for r in self._all_data if r["id"] == self._selected_id), None)
        if med is None:
            return
        self._var_name.set(med["name"])
        self._var_generic.set(med.get("generic") or "")
        self._var_strength.set(med.get("strength") or "")
        self._var_stock.set(med["stock"])
        self._var_price.set(str(med["price"]))
        self._var_expires.set(str(med["expires_date"]) if med["expires_date"] else "")
        self._selected_label.config(text=f"Selected ID: {self._selected_id}")
        self._btn_update.config(state="normal")
        self._btn_delete.config(state="normal")
        self._btn_save.config(state="disabled")

    # ── Table helpers ────────────────────────────────────────────
    def refresh_table(self):
        try:
            self._all_data = get_all_medicines()
            self._filter_table()
            self._update_stats(self._all_data)
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _filter_table(self):
        q = self._search_var.get().strip().lower()
        if q == self._search_placeholder.lower():
            q = ""
        filtered = [r for r in self._all_data
                    if any(q in value.lower() for value in
                           (r["name"], r.get("generic") or "", format_strength(r.get("strength"))))
                    or q.replace(" ", "") in (r.get("strength") or "").lower().replace(" ", "")]
        self._render_rows(filtered)

    def _render_rows(self, rows):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, r in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            tags = (tag, "low") if r["stock"] < 10 else (tag,)
            self._tree.insert("", "end", values=(
                r["id"], format_name(r["name"]), format_name(r.get("generic")), format_strength(r.get("strength")),
                r["stock"], f"{float(r['price']):.2f}", r["expires_date"] or ""
            ), tags=tags)
        count = len(rows)
        self._lbl_row_count.config(text=f"{count} medicine{'s' if count != 1 else ''} shown")

    def _update_stats(self, rows):
        low = sum(1 for r in rows if r["stock"] < 10)
        self._lbl_total.config(text=str(len(rows)))
        self._lbl_low.config(text=str(low), fg=DANGER if low else ACCENT)

    # ── Form utils ───────────────────────────────────────────────
    def _clear_form(self):
        for v in (self._var_name, self._var_generic, self._var_strength,
                  self._var_price, self._var_stock, self._var_expires):
            v.set("")
        self._selected_id = None
        self._selected_label.config(text="")
        self._btn_update.config(state="disabled")
        self._btn_delete.config(state="disabled")
        self._btn_save.config(state="normal")
        self._tree.selection_remove(self._tree.selection())
        self._set_status("")

    def _set_status(self, msg):
        if self._status_after_id is not None:
            self.after_cancel(self._status_after_id)
            self._status_after_id = None
        self._status.config(text=msg)
        if msg:
            self._status_after_id = self.after(4000, lambda: self._set_status(""))
