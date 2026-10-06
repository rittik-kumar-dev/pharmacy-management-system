"""Reports content for the persistent application shell."""
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal
from main import (BG, PANEL, TEXT, MUTED, ACCENT, BORDER, ROW_ODD, ROW_EVEN,
                  FONT_INPUT, FONT_SMALL, styled_button, format_name, format_strength)
from report import (get_sales_report, get_sale_header, get_sale_details, get_inventory_report,
                    get_alert_report, LOW_STOCK_THRESHOLD, EXPIRING_DAYS)


class ReportsFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller
        self._mode = "Sales"
        self._details_dialog = None
        self._build_ui()

    def on_show(self):
        self.refresh_report()

    def _build_ui(self):
        tk.Label(self, text="Reports", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(8, 12))
        tabs = tk.Frame(self, bg=BG)
        tabs.pack(fill="x", padx=12, pady=(0, 12))
        self._tabs = {}
        for mode in ("Sales", "Inventory", "Low Stock / Expiry"):
            button = styled_button(tabs, mode, lambda value=mode: self._switch_tab(value), width=20)
            button.pack(side="left", padx=(0, 8))
            self._tabs[mode] = button
        self._filters = tk.Frame(self, bg=BG)
        self._filters.pack(fill="x", padx=12, pady=(0, 10))
        self._from_var, self._to_var = tk.StringVar(), tk.StringVar()
        for label, variable in (("From Date", self._from_var), ("To Date", self._to_var)):
            tk.Label(self._filters, text=label, bg=BG, fg=MUTED,
                     font=FONT_SMALL).pack(side="left", padx=(0, 6))
            entry = tk.Entry(self._filters, textvariable=variable, width=13, bg=PANEL,
                            fg=TEXT, insertbackground=ACCENT, font=FONT_INPUT, relief="flat",
                            highlightthickness=1, highlightbackground=BORDER)
            entry.pack(side="left", padx=(0, 10), ipady=4)
            entry.bind("<Return>", lambda _event: self.refresh_report())
        styled_button(self._filters, "Apply", self.refresh_report, width=8).pack(side="left", padx=(0, 8))
        styled_button(self._filters, "Clear Filter", self._clear_filter, width=12).pack(side="left")
        self._hint = tk.Label(self, bg=BG, fg=MUTED, font=FONT_SMALL, anchor="w")
        self._hint.pack(fill="x", padx=12, pady=(0, 6))
        self._table_holder = tk.Frame(self, bg=BG)
        self._table_holder.pack(fill="both", expand=True, padx=12)
        self._tree = self._make_table(self._table_holder, height=7)
        self._tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self._tree.bind("<Double-1>", lambda _event: self._view_details() if self._mode == "Sales" else None)
        self._actions = tk.Frame(self, bg=BG)
        self._actions.pack(fill="x", padx=12, pady=8)
        self._details_button = styled_button(self._actions, "View Sale Details", self._view_details, width=18)
        self._details_button.pack(side="left")
        self._summary = tk.Label(self._actions, bg=BG, fg=ACCENT, font=FONT_INPUT)
        self._summary.pack(side="right")
        self._update_layout()

    def _make_table(self, parent, height):
        holder = tk.Frame(parent, bg=BG)
        holder.pack(fill="both", expand=True)
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        tree = ttk.Treeview(holder, show="headings", style="Pharmacy.Treeview",
                            selectmode="browse", height=height)
        tree.tag_configure("odd", background=ROW_ODD)
        tree.tag_configure("even", background=ROW_EVEN)
        vertical = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(holder, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self._vertical_scrollbar = vertical
        self._horizontal_scrollbar = horizontal
        return tree

    def _configure_columns(self, tree, columns):
        tree.configure(columns=columns)
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=180 if column in ("Medicine Name", "Status", "Date/Time") else 110,
                        minwidth=80, anchor="w", stretch=True)

    def _update_layout(self):
        for mode, button in self._tabs.items():
            button.config(bg=ACCENT if mode == self._mode else PANEL,
                          fg=BG if mode == self._mode else TEXT)
        self._filters.pack_forget()
        self._details_button.pack_forget()
        if self._mode == "Sales":
            self._filters.pack(fill="x", padx=12, pady=(0, 10), before=self._hint)
            self._details_button.pack(side="left")
        columns = {
            "Sales": ("Sale ID", "Date/Time", "Sold By", "Total Amount"),
            "Inventory": ("Medicine Name", "Group / Generic", "Strength", "Stock Quantity", "Price", "Expiry Date"),
            "Low Stock / Expiry": ("Medicine Name", "Strength", "Stock", "Expiry Date", "Status"),
        }
        self._configure_columns(self._tree, columns[self._mode])
        if self._mode == "Sales":
            # Keep IDs compact; the other columns share extra space as the app grows.
            for column, width, minimum, anchor, stretch in (
                    ("Sale ID", 80, 70, "center", False),
                    ("Date/Time", 320, 220, "w", True),
                    ("Sold By", 200, 140, "w", True),
                    ("Total Amount", 180, 140, "center", True)):
                self._tree.column(column, width=width, minwidth=minimum,
                                  anchor=anchor, stretch=stretch)
                self._tree.heading(column, anchor=anchor)
            self._horizontal_scrollbar.grid_remove()
        else:
            self._horizontal_scrollbar.grid()
        self._hide_details()

    def _switch_tab(self, mode):
        self._mode = mode
        self._update_layout()
        self.refresh_report()

    def _hide_details(self):
        self._details_button.config(state="disabled")

    def _selection_changed(self, _event=None):
        self._hide_details()
        if self._mode == "Sales" and self._tree.selection():
            self._details_button.config(state="normal")

    def _clear_filter(self):
        self._from_var.set("")
        self._to_var.set("")
        self.refresh_report()

    def refresh_report(self):
        try:
            if self._mode == "Sales":
                rows = get_sales_report(self._from_var.get(), self._to_var.get())
                values = [(r["id"], r["sale_date"].strftime("%Y-%m-%d %H:%M:%S"),
                           r["sold_by"], f"\u09f3{r['total_amount']:.2f}") for r in rows]
                total = sum((r["total_amount"] for r in rows), Decimal("0.00"))
                summary = f"Sales Count: {len(rows)}    Total Sales Amount: \u09f3{total:.2f}"
                hint = "Dates: YYYY-MM-DD. Leave either date empty for an open range."
            else:
                rows = get_inventory_report() if self._mode == "Inventory" else get_alert_report()
                values = []
                for r in rows:
                    name, strength = format_name(r["name"]), format_strength(r["strength"])
                    if self._mode == "Inventory":
                        values.append((name, format_name(r["generic"]), strength, r["stock"],
                                       f"\u09f3{r['price']:.2f}", r["expires_date"] or ""))
                    else:
                        values.append((name, strength, r["stock"], r["expires_date"] or "", r["status"]))
                summary = f"{len(rows)} medicines shown"
                hint = ("Current medicine inventory." if self._mode == "Inventory" else
                        f"Low Stock: at or below {LOW_STOCK_THRESHOLD}. Expiring Soon: today through {EXPIRING_DAYS} days ahead.")
        except ValueError as error:
            self._hint.config(text="Filter not applied. Displaying the previous results.")
            messagebox.showerror("Invalid Date Filter", str(error), parent=self)
            return
        except Exception as error:
            self._tree.delete(*self._tree.get_children())
            self._hide_details()
            self._summary.config(text="Report unavailable")
            messagebox.showerror("Database Error", f"Could not load report:\n{error}", parent=self)
            return
        self._tree.delete(*self._tree.get_children())
        self._hide_details()
        for index, (row, displayed) in enumerate(zip(rows, values)):
            self._tree.insert("", "end", iid=str(row["id"]), values=displayed,
                              tags=("odd" if index % 2 else "even",))
        self._summary.config(text=summary)
        self._hint.config(text=hint if rows else hint + " No matching records.")

    def _view_details(self):
        if self._details_dialog is not None and self._details_dialog.winfo_exists():
            self._details_dialog.lift()
            self._details_dialog.focus_set()
            return
        if self._mode != "Sales":
            return
        selected = self._tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a sale first.", parent=self)
            return
        try:
            sale_id = int(selected[0])
            header = get_sale_header(sale_id)
            if header is None:
                messagebox.showinfo("Sale Not Found", "This sale is no longer available.", parent=self)
                return
            rows = get_sale_details(sale_id)
        except Exception as error:
            messagebox.showerror("Database Error", f"Could not load sale details:\n{error}", parent=self)
            return
        self._details_dialog = SaleDetailsDialog(self.winfo_toplevel(), header, rows)


class SaleDetailsDialog(tk.Toplevel):
    """One modal, read-only detail window owned by the application root."""
    def __init__(self, parent, header, rows):
        super().__init__(parent)
        self.withdraw()
        self.title(f"Sale Details — #{header['id']}")
        self.configure(bg=BG)
        self.transient(parent)
        self.minsize(700, 430)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _event: self._close())
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(body, text=f"Sale Details — #{header['id']}", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 12))
        metadata = tk.Frame(body, bg=PANEL, padx=12, pady=8)
        metadata.pack(fill="x", pady=(0, 12))
        for label, value in (("Sale ID", header['id']),
                             ("Date/Time", header['sale_date'].strftime("%Y-%m-%d %H:%M:%S")),
                             ("Sold By", header['sold_by'])):
            tk.Label(metadata, text=f"{label}: {value}", bg=PANEL, fg=TEXT,
                     font=FONT_INPUT, anchor="w").pack(fill="x", pady=2)
        table = tk.Frame(body, bg=BG)
        table.pack(fill="both", expand=True)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        columns = ("Medicine Name", "Strength", "Quantity", "Unit Price", "Subtotal")
        self._tree = ttk.Treeview(table, columns=columns, show="headings", height=8,
                                 style="Pharmacy.Treeview", selectmode="browse")
        for column, width in zip(columns, (240, 130, 85, 115, 115)):
            self._tree.heading(column, text=column)
            self._tree.column(column, width=width, minwidth=60, stretch=True,
                              anchor="w" if column in ("Medicine Name", "Strength") else "center")
        self._tree.tag_configure("odd", background=ROW_ODD)
        self._tree.tag_configure("even", background=ROW_EVEN)
        self._scrollbar = ttk.Scrollbar(table, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=self._update_scrollbar)
        self._tree.grid(row=0, column=0, sticky="nsew")
        for index, row in enumerate(rows):
            self._tree.insert("", "end", values=(format_name(row["name"]),
                format_strength(row["strength"]), row["quantity"],
                f"\u09f3{row['unit_price']:.2f}", f"\u09f3{row['subtotal']:.2f}"),
                tags=("odd" if index % 2 else "even",))
        if not rows:
            tk.Label(body, text="No medicine items found for this sale.", bg=BG, fg=MUTED,
                     font=FONT_SMALL).pack(anchor="w", pady=(6, 0))
        footer = tk.Frame(body, bg=BG)
        footer.pack(fill="x", pady=(12, 0))
        self._total_label = tk.Label(footer, text=f"Total Amount: \u09f3{header['total_amount']:.2f}",
                                    bg=BG, fg=ACCENT, font=("Segoe UI", 11, "bold"))
        self._total_label.pack(side="left")
        self._close_button = styled_button(footer, "Close", self._close, width=10)
        self._close_button.pack(side="right")
        parent.update_idletasks()
        width, height = 840, 500
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        x = max(0, min(x, self.winfo_screenwidth() - width))
        y = max(0, min(y, self.winfo_screenheight() - height))
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.grab_set()
        self._close_button.focus_set()

    def _update_scrollbar(self, first, last):
        self._scrollbar.set(first, last)
        if float(first) > 0 or float(last) < 1:
            self._scrollbar.grid(row=0, column=1, sticky="ns")
        else:
            self._scrollbar.grid_remove()

    def _close(self):
        if self.grab_current() is self:
            self.grab_release()
        self.destroy()
