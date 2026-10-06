"""Real MySQL query and Tkinter checks; fixtures use temporary tables only."""
import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from db import conn
import report
from app import App


class ReportsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = ("sale_items", "sales", "medicines", "admins", "suppliers")
        cursor = conn.cursor()
        cls.snapshots = {}
        for table in cls.tables:
            cursor.execute(f"SELECT * FROM {table} ORDER BY id")
            cls.snapshots[table] = cursor.fetchall()
        conn.commit()
        for table in cls.tables:
            cursor.execute(f"CREATE TEMPORARY TABLE {table} AS SELECT source.* FROM {table} source WHERE 1=0")
        today = report.shop_now().date()
        cursor.execute("INSERT INTO admins (id,username,password_hash) VALUES (1,'report-admin','unused')")
        for ident, stock, days in ((1,10,-1),(2,11,0),(3,9,30),(4,50,31),(5,0,None)):
            cursor.execute("""INSERT INTO medicines
                (id,name,generic,strength,stock,price,expires_date) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (ident,f"Medicine {ident}","Generic","500mg",stock,Decimal("9.00"),
                 None if days is None else today+timedelta(days=days)))
        for ident, timestamp, total in ((1,"2026-10-05 23:59:59","5.00"),
                                       (2,"2026-10-06 00:00:00","10.00"),
                                       (3,"2026-10-06 23:59:59","15.00"),
                                       (4,"2026-10-07 00:00:00","20.00")):
            cursor.execute("INSERT INTO sales (id,sale_date,total_amount,sold_by) VALUES (%s,%s,%s,1)",
                           (ident,timestamp,total))
        cursor.execute("""INSERT INTO sale_items (sale_id,medicine_id,quantity,unit_price,subtotal)
                          VALUES (2,1,2,5.00,10.00)""")
        conn.commit()
        cursor.close()
        cls.app = App()
        cls.app.withdraw()
        cls.app.admin_username = "report-admin"

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()
        cursor = conn.cursor()
        for table in cls.tables:
            cursor.execute(f"DROP TEMPORARY TABLE {table}")
        conn.commit()
        for table, expected in cls.snapshots.items():
            cursor.execute(f"SELECT * FROM {table} ORDER BY id")
            assert cursor.fetchall() == expected, f"Saved {table} data changed"
        conn.commit()
        cursor.close()

    def test_sales_queries_and_validation(self):
        self.assertEqual(len(report.get_sales_report()),4)
        rows = report.get_sales_report("2026-10-06","2026-10-06")
        self.assertEqual([r['id'] for r in rows],[3,2])
        self.assertEqual(sum(r['total_amount'] for r in rows),Decimal('25.00'))
        self.assertEqual(rows[0]['sold_by'],'report-admin')
        self.assertEqual(len(report.get_sales_report("2026-10-06","")),3)
        self.assertEqual(len(report.get_sales_report("","2026-10-06")),3)
        self.assertEqual(report.get_sales_report("2027-01-01",""),[])
        self.assertEqual(len(report.get_sales_report("","9999-12-31")),4)
        for start,end in (("2026-2-01",""),("2026-02-30",""),("x",""),
                          ("","2026-13-01"),("2026-10-07","2026-10-06")):
            with self.assertRaises(ValueError):
                report.get_sales_report(start,end)

    def test_details_inventory_and_alerts(self):
        details = report.get_sale_details(2)
        self.assertEqual(len(details),1)
        self.assertEqual(details[0]['unit_price'],Decimal('5.00'))
        self.assertEqual(details[0]['subtotal'],Decimal('10.00'))
        self.assertEqual(details[0]['quantity'],2)
        self.assertEqual(report.get_sale_details(999),[])
        self.assertEqual(report.get_sale_header(2)['total_amount'], Decimal('10.00'))
        self.assertEqual(report.get_sale_header(2)['sold_by'], 'report-admin')
        self.assertIsNone(report.get_sale_header(999))
        self.assertEqual(len(report.get_inventory_report()),5)
        statuses = {r['id']:r['status'] for r in report.get_alert_report()}
        self.assertEqual(statuses,{1:'Low Stock, Expired',2:'Expiring Soon',
                                   3:'Low Stock, Expiring Soon',5:'Low Stock'})

    def test_ui_filters_details_and_navigation(self):
        app = self.app
        frame = app.frames['ReportsFrame']
        app._nav_buttons['ReportsFrame'].invoke()
        self.assertEqual(len(frame._tree.get_children()),4)
        self.assertIn('Sales Count: 4', frame._summary.cget('text'))
        self.assertIn('Total Sales Amount:', frame._summary.cget('text'))
        for start, end, expected_count in (('2026-10-06', '', 3),
                                            ('', '2026-10-06', 3), ('', '', 4)):
            frame._from_var.set(start)
            frame._to_var.set(end)
            frame.refresh_report()
            self.assertEqual(len(frame._tree.get_children()), expected_count)
        frame._from_var.set('2026-10-06')
        frame._to_var.set('2026-10-06')
        frame.refresh_report()
        self.assertEqual(len(frame._tree.get_children()),2)
        self.assertIn('25.00',frame._summary.cget('text'))
        for start, end in (('invalid', ''), ('', '2026-02-30'),
                           ('2026-10-07', '2026-10-06')):
            frame._from_var.set(start)
            frame._to_var.set(end)
            with patch('reports.messagebox.showerror') as error:
                frame.refresh_report()
                error.assert_called_once()
                self.assertEqual(error.call_args.args[0], 'Invalid Date Filter')
                self.assertIn('Filter not applied', frame._hint.cget('text'))
        frame._clear_filter()
        frame._tree.selection_set('2')
        frame._selection_changed()
        app.deiconify()
        app.update()
        frame._view_details()
        dialog = frame._details_dialog
        app.update()
        self.assertEqual(dialog.title(), 'Sale Details — #2')
        self.assertEqual(str(dialog.transient()), str(app))
        self.assertIs(app.grab_current(), dialog)
        self.assertEqual(len(dialog._tree.get_children()),1)
        self.assertEqual(tuple(dialog._tree['columns']),
                         ('Medicine Name', 'Strength', 'Quantity', 'Unit Price', 'Subtotal'))
        detail = dialog._tree.item(dialog._tree.get_children()[0], 'values')
        self.assertEqual(tuple(str(value) for value in detail),
                         ('Medicine 1', '500 mg', '2', '\u09f35.00', '\u09f310.00'))
        self.assertEqual(dialog._total_label.cget('text'), 'Total Amount: \u09f310.00')
        self.assertEqual(dialog._scrollbar.winfo_manager(), '')
        self.assertEqual(dialog.winfo_x(), app.winfo_rootx() + (app.winfo_width()-840)//2)
        self.assertEqual(dialog.winfo_y(), app.winfo_rooty() + (app.winfo_height()-500)//2)
        frame._view_details()
        self.assertIs(frame._details_dialog, dialog)
        dialog._close_button.invoke()
        self.assertFalse(dialog.winfo_exists())
        self.assertIsNone(app.grab_current())
        self.assertTrue(app.winfo_exists())
        self.assertFalse(hasattr(frame, '_details'))
        with patch('reports.get_sale_details', side_effect=RuntimeError('Unavailable')), \
                patch('reports.messagebox.showerror') as error:
            frame._view_details()
            error.assert_called_once()
            self.assertFalse(frame._details_dialog.winfo_exists())
        frame._tree.selection_remove(frame._tree.selection())
        with patch('reports.messagebox.showinfo') as info:
            frame._view_details()
            self.assertEqual(info.call_args.args[1], 'Please select a sale first.')
        frame._tree.selection_set('2')
        many_rows = report.get_sale_details(2) * 12
        with patch('reports.get_sale_details', return_value=many_rows):
            frame._view_details()
        dialog = frame._details_dialog
        app.update()
        self.assertEqual(dialog._scrollbar.winfo_manager(), 'grid')
        dialog.geometry('840x1000')
        app.update()
        self.assertEqual(dialog._scrollbar.winfo_manager(), '')
        dialog._close()
        frame._tree.selection_set('1')
        frame._view_details()
        app.update()
        self.assertEqual(len(frame._details_dialog._tree.get_children()), 0)
        frame._details_dialog._close()
        app.withdraw()
        frame._switch_tab('Inventory')
        self.assertEqual(len(frame._tree.get_children()),5)
        self.assertEqual(tuple(frame._tree['columns']),
                         ('Medicine Name', 'Group / Generic', 'Strength', 'Stock Quantity', 'Price', 'Expiry Date'))
        self.assertEqual(set(frame._tree.get_children()), {'1', '2', '3', '4', '5'})
        frame._switch_tab('Low Stock / Expiry')
        self.assertEqual(len(frame._tree.get_children()),4)
        self.assertEqual(frame._tree['columns'][-1], 'Status')
        self.assertEqual(frame._tree.item('1', 'values')[-1], 'Low Stock, Expired')
        self.assertEqual(frame._tree.item('3', 'values')[-1], 'Low Stock, Expiring Soon')
        frame._switch_tab('Sales')
        frame._from_var.set('2027-01-01')
        frame.refresh_report()
        self.assertEqual(len(frame._tree.get_children()),0)
        self.assertIn('Sales Count: 0',frame._summary.cget('text'))
        frame._clear_filter()
        def widget_count(widget):
            return 1+sum(widget_count(child) for child in widget.winfo_children())
        # Dashboard builds its recent-medicine rows on first display.
        for name in ('DashboardFrame','MedicineFrame','SalesFrame','SupplierFrame','ReportsFrame'):
            app.show_frame(name)
        count = widget_count(app)
        identities = {name:id(value) for name,value in app.frames.items()}
        for _ in range(12):
            for name in ('DashboardFrame','ReportsFrame','MedicineFrame','ReportsFrame',
                         'SalesFrame','ReportsFrame','SupplierFrame','ReportsFrame'):
                app.show_frame(name)
                app.update_idletasks()
        self.assertEqual(widget_count(app),count)
        self.assertEqual({name:id(value) for name,value in app.frames.items()},identities)
        with patch('reports.get_sales_report',wraps=report.get_sales_report) as read:
            app.show_frame('ReportsFrame')
            read.assert_called_once()


if __name__ == '__main__':
    unittest.main()
