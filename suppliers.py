import re
import tkinter as tk
from tkinter import ttk, messagebox
from main import (BG, PANEL, ACCENT, DANGER, TEXT, MUTED, BORDER, ROW_ODD,
                  ROW_EVEN, FONT_INPUT, FONT_SMALL, labeled_entry, styled_button)
from supplier import (add_supplier, get_all_suppliers, search_suppliers,
                      update_supplier, delete_supplier)


class SupplierFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller
        self._selected_id = None
        self._all_data = []
        self._status_after_id = None
        self._build_ui()

    def on_show(self):
        self.refresh_table()

    def _build_ui(self):
        tk.Label(self, text="Supplier Management", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(8, 4))
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_main(body)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=PANEL, width=280)
        sidebar.pack(side="left", fill="y", padx=(12, 6), pady=12)
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="Supplier Details", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(18, 4))
        self._selected_label = tk.Label(sidebar, text="", bg=PANEL, fg=MUTED, font=FONT_SMALL)
        self._selected_label.pack(fill="x", padx=18, pady=(0, 4))
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=18, pady=(0, 8))
        form = tk.Frame(sidebar, bg=PANEL)
        form.pack(fill="x", padx=18)
        form.columnconfigure(1, weight=1)
        self._vars = {}
        for row, (field, label) in enumerate((("name", "Supplier Name"),
                ("contact_person", "Contact Person"), ("phone", "Phone"),
                ("email", "Email"), ("address", "Address"))):
            self._vars[field] = labeled_entry(form, label, row)
        buttons = tk.Frame(sidebar, bg=PANEL)
        buttons.pack(fill="x", padx=18, pady=(18, 0))
        self._btn_save = styled_button(buttons, "Add", self._on_save, width=12)
        self._btn_update = styled_button(buttons, "Update", self._on_update,
                                         color="#3B82F6", fg=TEXT, width=12)
        self._btn_delete = styled_button(buttons, "Delete", self._on_delete,
                                         color=DANGER, fg=TEXT, width=12)
        for button in (self._btn_save, self._btn_update, self._btn_delete):
            button.pack(fill="x", pady=(0, 6))
        self._btn_update.config(state="disabled")
        self._btn_delete.config(state="disabled")
        styled_button(buttons, "Clear", self._clear_form, color=BORDER,
                      fg=MUTED, width=12).pack(fill="x")
        self._status = tk.Label(sidebar, text="", bg=PANEL, fg=ACCENT,
                                font=FONT_SMALL, wraplength=244, justify="left")
        self._status.pack(fill="x", padx=18, pady=(12, 0))

    def _build_main(self, parent):
        main = tk.Frame(parent, bg=BG)
        main.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=12)
        tk.Label(main, text="Search by supplier name, contact person or phone",
                 bg=BG, fg=MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        self._search_var = tk.StringVar()
        search = tk.Entry(main, textvariable=self._search_var, font=FONT_INPUT,
                          bg=PANEL, fg=TEXT, insertbackground=ACCENT, relief="flat",
                          highlightthickness=1, highlightbackground=BORDER,
                          highlightcolor=ACCENT)
        search.pack(fill="x", ipady=7, pady=(0, 8))
        cols = ("ID", "Supplier Name", "Contact Person", "Phone", "Email", "Address")
        frame_tree = tk.Frame(main, bg=BG)
        frame_tree.pack(fill="both", expand=True)
        # MedicineFrame configures this shared dark Treeview style at startup.
        self._tree = ttk.Treeview(frame_tree, columns=cols, show="headings",
                                  style="Pharmacy.Treeview", selectmode="browse")
        widths = dict(zip(cols, (35, 115, 115, 100, 130, 140)))
        for col in cols:
            self._tree.heading(col, text=col, anchor="center")
            self._tree.column(col, width=widths[col], minwidth=widths[col],
                              anchor="center" if col == "ID" else "w")
        self._tree.tag_configure("odd", background=ROW_ODD)
        self._tree.tag_configure("even", background=ROW_EVEN)
        vertical = ttk.Scrollbar(frame_tree, orient="vertical", command=self._tree.yview)
        horizontal = ttk.Scrollbar(frame_tree, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        frame_tree.rowconfigure(0, weight=1)
        frame_tree.columnconfigure(0, weight=1)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self._lbl_row_count = tk.Label(main, text="", bg=BG, fg=MUTED, font=FONT_SMALL)
        self._lbl_row_count.pack(anchor="w", pady=(8, 0))
        self._search_var.trace_add("write", lambda *_: self._filter_table())

    def _fields(self):
        return tuple(self._vars[field].get().strip() for field in
                     ("name", "contact_person", "phone", "email", "address"))

    def _validate(self, name, contact_person, phone, email, address):
        phone = phone.strip()
        email = email.strip()
        if not name or not phone:
            messagebox.showerror("Missing Fields", "Supplier name and phone are required.")
            return False
        if not re.fullmatch(r"01[0-9]{9}", phone):
            messagebox.showerror("Invalid Phone", "Phone number must be 11 digits and start with 01.")
            return False
        for label, value, limit in (("Supplier name", name, 100),
                ("Contact person", contact_person, 100), ("Phone", phone, 20),
                ("Email", email, 100), ("Address", address, 255)):
            if len(value) > limit:
                messagebox.showerror("Invalid Details", f"{label} must be at most {limit} characters.")
                return False
        email_pattern = (
            r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
            r"(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
        )
        if email and (not re.fullmatch(email_pattern, email)
                      or len(email.split("@", 1)[0]) > 64
                      or any(len(label) > 63 for label in email.rsplit("@", 1)[-1].split("."))):
            messagebox.showerror("Invalid Email", "Enter a valid email address, or leave email blank.")
            return False
        return True

    def _on_save(self):
        fields = self._fields()
        if not self._validate(*fields):
            return
        try:
            add_supplier(*fields)
            self._clear_form()
            self._set_status("Supplier added successfully.")
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_update(self):
        if self._selected_id is None:
            messagebox.showinfo("No Selection", "Select a supplier to update.")
            return
        fields = self._fields()
        if not self._validate(*fields):
            return
        try:
            update_supplier(self._selected_id, *fields)
            self._clear_form()
            self._set_status("Supplier updated successfully.")
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_delete(self):
        if self._selected_id is None:
            messagebox.showinfo("No Selection", "Select a supplier to delete.")
            return
        if not messagebox.askyesno("Confirm Delete",
                f"Delete '{self._vars['name'].get()}'?\nThis cannot be undone."):
            return
        try:
            delete_supplier(self._selected_id)
            self._clear_form()
            self._set_status("Supplier deleted successfully.")
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _on_row_select(self, _event):
        selected = self._tree.selection()
        if not selected:
            return
        supplier_id = int(self._tree.item(selected[0], "values")[0])
        supplier = next((row for row in self._all_data if row["id"] == supplier_id), None)
        if supplier is None:
            return
        self._selected_id = supplier_id
        for field, var in self._vars.items():
            var.set(supplier.get(field) or "")
        self._selected_label.config(text=f"Selected ID: {supplier_id}")
        self._btn_save.config(state="disabled")
        self._btn_update.config(state="normal")
        self._btn_delete.config(state="normal")

    def refresh_table(self):
        try:
            self._all_data = get_all_suppliers()
            if self._selected_id is not None and not any(
                    row["id"] == self._selected_id for row in self._all_data):
                self._clear_form()
            self._filter_table()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _filter_table(self):
        self._render_rows(search_suppliers(self._search_var.get(), self._all_data))

    def _render_rows(self, rows):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, row in enumerate(rows):
            self._tree.insert("", "end", values=tuple(row.get(field) or "" for field in
                ("id", "name", "contact_person", "phone", "email", "address")),
                tags=("odd" if i % 2 else "even",))
        self._lbl_row_count.config(text=f"{len(rows)} suppliers shown")

    def _clear_form(self):
        for var in self._vars.values():
            var.set("")
        self._selected_id = None
        self._selected_label.config(text="")
        self._btn_save.config(state="normal")
        self._btn_update.config(state="disabled")
        self._btn_delete.config(state="disabled")
        self._tree.selection_remove(self._tree.selection())
        self._set_status("")

    def _set_status(self, msg):
        if self._status_after_id is not None:
            self.after_cancel(self._status_after_id)
            self._status_after_id = None
        self._status.config(text=msg)
        if msg:
            self._status_after_id = self.after(4000, lambda: self._set_status(""))
