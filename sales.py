import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal
from main import (BG, PANEL, TEXT, MUTED, ACCENT, BORDER, ROW_ODD, ROW_EVEN,
                  DANGER, FONT_INPUT, FONT_SMALL, styled_button, format_name, format_strength)
from medicine import get_all_medicines, get_medicine_by_id
from sale import (add_to_cart, complete_sale, SaleError, PriceChanged,
                  CheckoutUncertain, shop_now)


class SalesFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller
        self._cart = {}
        self._all_data = []
        self._selected_id = None
        self._busy = False
        self._checkout_uncertain = False
        self._build_ui()

    def on_show(self):
        self.refresh_medicines()

    def _build_ui(self):
        tk.Label(self, text="Sales / Billing", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(8, 4))
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(4, weight=1)
        search_row = tk.Frame(body, bg=BG)
        search_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(search_row, text="Search Medicine", bg=BG, fg=MUTED,
                 font=FONT_SMALL).pack(side="left", padx=(0, 10))
        self._search_var = tk.StringVar()
        tk.Entry(search_row, textvariable=self._search_var, font=FONT_INPUT,
                 bg=PANEL, fg=TEXT, insertbackground=ACCENT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True, ipady=4)
        self._medicine_tree = self._make_table(body, 1,
            ("Medicine Name", "Generic", "Strength", "Available Stock", "Unit Price", "Expiry Date"),
            (160, 145, 100, 110, 90, 105))
        self._medicine_tree.tag_configure("unavailable", foreground=DANGER)
        self._medicine_tree.bind("<<TreeviewSelect>>", self._on_select)
        selection = tk.Frame(body, bg=PANEL)
        selection.grid(row=2, column=0, sticky="ew", pady=6)
        selection.columnconfigure(0, weight=1)
        self._selected_label = tk.Label(selection, text="Select a medicine above.",
            bg=PANEL, fg=TEXT, font=FONT_SMALL, anchor="w", justify="left", wraplength=430)
        self._selected_label.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        tk.Label(selection, text="Quantity", bg=PANEL, fg=TEXT,
                 font=FONT_SMALL).grid(row=0, column=1, padx=(4, 6))
        self._quantity_var = tk.StringVar(value="1")
        quantity = tk.Entry(selection, textvariable=self._quantity_var, width=7,
            bg="#262A38", fg=TEXT, insertbackground=ACCENT, font=FONT_INPUT, relief="flat")
        quantity.grid(row=0, column=2, ipady=4, padx=(0, 8))
        quantity.bind("<Return>", lambda _e: self._on_add())
        self._btn_add = styled_button(selection, "Add to Cart", self._on_add, width=12)
        self._btn_add.grid(row=0, column=3, padx=(0, 8), pady=6)
        self._btn_add.config(state="disabled")
        tk.Label(body, text="Cart", bg=BG, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 4))
        self._cart_tree = self._make_table(body, 4,
            ("Medicine", "Strength", "Unit Price", "Quantity", "Subtotal"),
            (220, 120, 110, 90, 120))
        actions = tk.Frame(body, bg=BG)
        actions.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        styled_button(actions, "Remove Item", self._on_remove, color=BORDER,
                      fg=TEXT, width=12).pack(side="left")
        self._btn_complete = styled_button(actions, "Complete Sale", self._on_complete, width=14)
        self._btn_complete.pack(side="right")
        self._total_label = tk.Label(actions, text="", bg=BG, fg=ACCENT,
                                     font=("Segoe UI", 12, "bold"))
        self._total_label.pack(side="right", padx=14)
        self._search_var.trace_add("write", lambda *_: self._filter_medicines())
        self._render_cart()

    def _make_table(self, parent, row, columns, widths):
        holder = tk.Frame(parent, bg=BG)
        holder.grid(row=row, column=0, sticky="nsew")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        tree = ttk.Treeview(holder, columns=columns, show="headings", height=4,
                            style="Pharmacy.Treeview", selectmode="browse")
        for column, width in zip(columns, widths):
            tree.heading(column, text=column)
            tree.column(column, width=width, minwidth=min(width, 80),
                        anchor="w" if column in ("Medicine", "Medicine Name", "Generic") else "center")
        tree.tag_configure("odd", background=ROW_ODD)
        tree.tag_configure("even", background=ROW_EVEN)
        vertical = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(holder, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        return tree

    def refresh_medicines(self):
        try:
            self._all_data = get_all_medicines()
            self._filter_medicines()
            if self._selected_id is not None:
                medicine = next((m for m in self._all_data if m["id"] == self._selected_id), None)
                if medicine:
                    self._show_selection(medicine)
                else:
                    self._reset_selection()
        except Exception as error:
            messagebox.showerror("Database Error", str(error))

    def _filter_medicines(self):
        query = self._search_var.get().strip().casefold()
        for item in self._medicine_tree.get_children():
            self._medicine_tree.delete(item)
        today = shop_now().date()
        for index, medicine in enumerate(self._all_data):
            values = (format_name(medicine["name"]), format_name(medicine.get("generic")),
                      format_strength(medicine.get("strength")))
            if not any(query in value.casefold() for value in values) and query.replace(" ", "") not in values[2].casefold().replace(" ", ""):
                continue
            tags = ("odd" if index % 2 else "even",)
            expiry = medicine.get("expires_date")
            if medicine["stock"] <= 0 or expiry is None or expiry < today:
                tags += ("unavailable",)
            self._medicine_tree.insert("", "end", iid=str(medicine["id"]),
                values=values+(medicine["stock"], f"{medicine['price']:.2f}", expiry or ""), tags=tags)

    def _on_select(self, _event):
        selected = self._medicine_tree.selection()
        if selected:
            self._selected_id = int(selected[0])
            medicine = next(m for m in self._all_data if m["id"] == self._selected_id)
            self._show_selection(medicine)

    def _show_selection(self, medicine):
        self._selected_label.config(text=f"{format_name(medicine['name'])} | {format_name(medicine.get('generic'))} | {format_strength(medicine.get('strength'))}\nStock: {medicine['stock']} | Unit price: \u09f3{medicine['price']:.2f}")
        self._btn_add.config(state="normal")

    def _reset_selection(self):
        self._selected_id = None
        self._quantity_var.set("1")
        self._selected_label.config(text="Select a medicine above.")
        self._btn_add.config(state="disabled")
        self._medicine_tree.selection_remove(self._medicine_tree.selection())

    def _on_add(self):
        if self._selected_id is None:
            messagebox.showinfo("No Selection", "Select a medicine to add to the cart.")
            return
        try:
            medicine = get_medicine_by_id(self._selected_id)
            if medicine is None:
                raise SaleError("This medicine no longer exists.")
            add_to_cart(self._cart, medicine, self._quantity_var.get())
            self._render_cart()
        except PriceChanged as error:
            self._apply_prices(error.prices)
            messagebox.showwarning("Price Changed", str(error))
        except SaleError as error:
            messagebox.showerror("Cannot Add Medicine", str(error))
        except Exception as error:
            messagebox.showerror("Database Error", str(error))

    def _apply_prices(self, prices):
        for medicine_id, price in prices.items():
            if medicine_id in self._cart:
                self._cart[medicine_id]["unit_price"] = price
        self._render_cart()

    def _on_remove(self):
        selected = self._cart_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Select a cart item to remove.")
            return
        self._cart.pop(int(selected[0]), None)
        self._render_cart()

    def _render_cart(self):
        for item in self._cart_tree.get_children():
            self._cart_tree.delete(item)
        total = Decimal("0.00")
        for index, (medicine_id, item) in enumerate(self._cart.items()):
            subtotal = item["unit_price"] * item["quantity"]
            total += subtotal
            self._cart_tree.insert("", "end", iid=str(medicine_id), values=(
                format_name(item["name"]), format_strength(item["strength"]),
                f"{item['unit_price']:.2f}", item["quantity"], f"{subtotal:.2f}"),
                tags=("odd" if index % 2 else "even",))
        self._total_label.config(text=f"Total: \u09f3{total:.2f}")
        self._btn_complete.config(state="normal" if self._cart and not self._busy and not self._checkout_uncertain else "disabled")

    def clear_cart(self):
        self._cart.clear()
        self._reset_selection()
        self._render_cart()

    def _on_complete(self):
        if self._busy or self._checkout_uncertain:
            return
        self._busy = True
        self._btn_complete.config(state="disabled")
        try:
            sale_id = complete_sale(self.controller.admin_username, self._cart)
        except PriceChanged as error:
            self._apply_prices(error.prices)
            messagebox.showwarning("Price Changed", str(error))
        except CheckoutUncertain as error:
            self._checkout_uncertain = True
            messagebox.showerror("Checkout Status Uncertain", str(error))
        except SaleError as error:
            messagebox.showerror("Sale Not Completed", str(error))
        except Exception as error:
            messagebox.showerror("Sale Not Completed", f"The sale was rolled back. {error}")
        else:
            self.clear_cart()
            messagebox.showinfo("Sale Completed", f"Sale ID {sale_id} completed successfully.")
            self.refresh_medicines()
            self.controller.frames["DashboardFrame"].on_show()
        finally:
            self._busy = False
            self._render_cart()
