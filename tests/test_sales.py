"""Run: python -m unittest discover -s tests -v. Uses connection-local temporary tables."""
import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import sale
from db import conn


class SalesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshots = {}
        cursor = conn.cursor()
        for table in ('admins', 'medicines', 'suppliers', 'madicines', 'sales', 'sale_items'):
            cursor.execute(f'SELECT * FROM `{table}` ORDER BY id')
            cls.snapshots[table] = cursor.fetchall()
        conn.commit()
        # Temporary tables shadow real names only on this connection, and disappear on close.
        for table, columns in (
            ('admins', 'id INT PRIMARY KEY, username VARCHAR(50)'),
            ('medicines', 'id INT PRIMARY KEY,name VARCHAR(100),generic VARCHAR(100),strength VARCHAR(100),price DECIMAL(10,2),stock INT,expires_date DATE'),
            ('sales', 'id INT AUTO_INCREMENT PRIMARY KEY,sale_date DATETIME,total_amount DECIMAL(10,2),sold_by INT'),
            ('sale_items', 'id INT AUTO_INCREMENT PRIMARY KEY,sale_id INT,medicine_id INT,quantity INT,unit_price DECIMAL(10,2),subtotal DECIMAL(10,2)')):
            cursor.execute(f'CREATE TEMPORARY TABLE `{table}` ({columns}) ENGINE=InnoDB')
        cursor.execute("INSERT INTO admins VALUES (1,'sales-test-admin')")
        conn.commit()
        cursor.close()

    @classmethod
    def tearDownClass(cls):
        conn.close()  # Automatically removes only the connection's temporary tables.
        # Verify real data through a fresh connection using the existing connection settings.
        import ast
        from pathlib import Path
        import mysql.connector
        module = ast.parse(Path('db.py').read_text(encoding='utf-8'))
        call = next(n for n in ast.walk(module) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == 'connect')
        check = mysql.connector.connect(**{k.arg: ast.literal_eval(k.value) for k in call.keywords})
        cursor = check.cursor()
        try:
            for table, rows in cls.snapshots.items():
                cursor.execute(f'SELECT * FROM `{table}` ORDER BY id')
                assert cursor.fetchall() == rows, table + ' changed'
        finally:
            cursor.close()
            check.close()

    def fixture(self, stock=10, days=1, price='2.50'):
        cursor = conn.cursor()
        cursor.execute('SELECT COALESCE(MAX(id),0)+1 FROM medicines')
        ident = cursor.fetchone()[0]
        cursor.execute('INSERT INTO medicines VALUES (%s,%s,%s,%s,%s,%s,%s)',
                       (ident, 'Napa', 'Paracetamol', '500 mg', price, stock,
                        sale.shop_now().date()+timedelta(days=days)))
        conn.commit()
        cursor.close()
        return dict(id=ident,name='Napa',generic='Paracetamol',strength='500 mg',
                    price=Decimal(price),stock=stock,expires_date=sale.shop_now().date()+timedelta(days=days))

    def snapshot(self):
        cursor = conn.cursor()
        result = []
        for table in ('medicines','sales','sale_items'):
            cursor.execute(f'SELECT * FROM {table} ORDER BY id')
            result.append(cursor.fetchall())
        conn.commit()
        cursor.close()
        return result

    def test_cart_and_success(self):
        med = self.fixture(days=0)
        cart = {}
        before = self.snapshot()
        sale.add_to_cart(cart,med,'2')
        sale.add_to_cart(cart,med,'3')
        self.assertEqual(len(cart),1)
        self.assertEqual(cart[med['id']]['quantity'],5)
        self.assertEqual(before,self.snapshot())
        other = self.fixture(price='1.25')
        sale.add_to_cart(cart,other,2)
        ident = sale.complete_sale('sales-test-admin',cart)
        cursor = conn.cursor()
        cursor.execute('SELECT total_amount FROM sales WHERE id=%s',(ident,))
        self.assertEqual(cursor.fetchone()[0],Decimal('15.00'))
        cursor.execute('SELECT stock FROM medicines WHERE id=%s',(med['id'],))
        self.assertEqual(cursor.fetchone()[0],5)
        cursor.execute('SELECT COUNT(*) FROM sale_items WHERE sale_id=%s',(ident,))
        self.assertEqual(cursor.fetchone()[0],2)
        cursor.close();conn.commit()

    def test_invalid_cart_inputs(self):
        for qty in ('',0,-1,'1.5','abc',True,'9'*5000):
            with self.assertRaises(sale.SaleError):sale.purchase_quantity(qty)
        for med in (self.fixture(stock=0),self.fixture(days=-1)):
            with self.assertRaises(sale.SaleError):sale.add_to_cart({},med,1)
        med=self.fixture(stock=2)
        with self.assertRaises(sale.SaleError):sale.add_to_cart({},med,3)
        med['expires_date']=None
        with self.assertRaises(sale.SaleError):sale.add_to_cart({},med,1)

    def test_checkout_revalidation(self):
        for column,value in (('stock',0),('expires_date',sale.shop_now().date()-timedelta(days=1)),('price',Decimal('3.00'))):
            med=self.fixture();cart={};sale.add_to_cart(cart,med,1)
            cursor=conn.cursor();cursor.execute(f'UPDATE medicines SET {column}=%s WHERE id=%s',(value,med['id']));conn.commit();cursor.close()
            before=self.snapshot()
            with self.assertRaises(sale.SaleError):sale.complete_sale('sales-test-admin',cart)
            self.assertEqual(before,self.snapshot())
        with self.assertRaises(sale.SaleError):sale.complete_sale('sales-test-admin',{})
        med=self.fixture();cart={};sale.add_to_cart(cart,med,1)
        with self.assertRaises(sale.SaleError):sale.complete_sale('missing-admin',cart)
        cart[999999] = dict(quantity=1,unit_price=Decimal('1.00'))
        with self.assertRaises(sale.SaleError):sale.complete_sale('sales-test-admin',cart)

    def test_rollback_after_partial_write(self):
        cart={}
        for i in range(2):sale.add_to_cart(cart,self.fixture(),1)
        before=self.snapshot()
        real_cursor=conn.cursor
        class FailingCursor:
            def __init__(self, wrapped):self.wrapped=wrapped;self.insertions=0
            def __getattr__(self,name):return getattr(self.wrapped,name)
            def execute(self,sql,params=None):
                if 'INSERT INTO sale_items' in sql:
                    self.insertions+=1
                    if self.insertions==2:raise RuntimeError('Injected second-item failure')
                return self.wrapped.execute(sql,params)
        with patch.object(conn,'cursor',side_effect=lambda **kw:FailingCursor(real_cursor(**kw))):
            with self.assertRaises(RuntimeError):sale.complete_sale('sales-test-admin',cart)
        self.assertEqual(before,self.snapshot())

    def test_guarded_stock_update_failure(self):
        cart={};sale.add_to_cart(cart,self.fixture(),1)
        before=self.snapshot()
        real_cursor=conn.cursor
        class GuardFailure:
            def __init__(self,wrapped):self.wrapped=wrapped;self.failed=False
            def __getattr__(self,name):return getattr(self.wrapped,name)
            @property
            def rowcount(self):return 0 if self.failed else self.wrapped.rowcount
            def execute(self,sql,params=None):
                result=self.wrapped.execute(sql,params)
                if sql.startswith('UPDATE medicines SET stock=stock-'):self.failed=True
                return result
        with patch.object(conn,'cursor',side_effect=lambda **kw:GuardFailure(real_cursor(**kw))):
            with self.assertRaises(sale.SaleError):sale.complete_sale('sales-test-admin',cart)
        self.assertEqual(before,self.snapshot())

    def test_amount_limits_and_historical_price(self):
        for price in ('0','-1','NaN','Infinity','1.001'):
            with self.assertRaises(sale.SaleError):sale.money(price)
        med=self.fixture(price='99999999.99')
        with self.assertRaises(sale.SaleError):sale.add_to_cart({},med,2)
        med=self.fixture();cart={};sale.add_to_cart(cart,med,1)
        ident=sale.complete_sale('sales-test-admin',cart)
        cursor=conn.cursor()
        cursor.execute('UPDATE medicines SET price=%s WHERE id=%s',(Decimal('4.00'),med['id']))
        conn.commit()
        cursor.execute('SELECT unit_price FROM sale_items WHERE sale_id=%s',(ident,))
        self.assertEqual(cursor.fetchone()[0],Decimal('2.50'))
        cursor.close();conn.commit()


class SalesUITests(unittest.TestCase):
    def frame(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from sales import SalesFrame
        class Variable:
            def __init__(self, value): self.value = value
            def get(self): return self.value
            def set(self, value): self.value = value
        class Tree:
            def __init__(self): self.rows = {}; self.selected = ()
            def get_children(self): return list(self.rows)
            def delete(self, item): self.rows.pop(item)
            def insert(self, parent, index, iid, values, tags): self.rows[iid] = values
            def selection(self): return self.selected
            def selection_remove(self, selected): self.selected = ()
        frame = SalesFrame.__new__(SalesFrame)
        frame._cart = {}; frame._all_data = []; frame._selected_id = 1
        frame._busy = False; frame._checkout_uncertain = False
        frame._quantity_var = Variable('2'); frame._search_var = Variable('')
        frame._medicine_tree = Tree(); frame._cart_tree = Tree()
        for attribute in ('_selected_label','_total_label','_btn_complete','_btn_add','tkraise'):
            setattr(frame, attribute, Mock())
        frame.controller = SimpleNamespace(admin_username='Admin', frames={'DashboardFrame':Mock()})
        frame.refresh_medicines = Mock()
        return frame

    def test_cart_ui_and_expiry(self):
        import sales
        frame = self.frame()
        med = dict(id=1,name='napa',generic='paracetamol',strength='500mg',
                   price=Decimal('2.50'),stock=10,expires_date=sale.shop_now().date())
        with patch('sales.get_medicine_by_id',return_value=med), patch.object(sales.messagebox,'showerror') as error:
            frame._on_add(); frame._on_add()
            self.assertEqual(len(frame._cart_tree.rows),1)
            self.assertEqual(frame._cart[1]['quantity'],4)
            frame._cart_tree.selected=('1',); frame._on_remove()
            self.assertFalse(frame._cart)
            med['expires_date'] -= timedelta(days=1)
            frame._on_add();self.assertFalse(frame._cart);error.assert_called_once()

    def test_checkout_ui_cleanup_price_change_and_uncertainty(self):
        import sales
        frame=self.frame()
        frame._cart={1:dict(name='Napa',strength='500 mg',unit_price=Decimal('2.50'),quantity=2)}
        with patch('sales.complete_sale',side_effect=sale.PriceChanged({1:Decimal('3.00')})), patch.object(sales.messagebox,'showwarning'):
            frame._on_complete()
            self.assertEqual(frame._cart[1]['unit_price'],Decimal('3.00'))
        with patch('sales.complete_sale',return_value=7) as checkout, patch.object(sales.messagebox,'showinfo') as info:
            frame._on_complete()
            self.assertFalse(frame._cart)
            self.assertIsNone(frame._selected_id)
            frame.controller.frames['DashboardFrame'].on_show.assert_called_once()
            self.assertIn('7', info.call_args.args[1])
        frame._cart={1:dict(name='Napa',strength='500 mg',unit_price=Decimal('2.50'),quantity=2)}
        with patch('sales.complete_sale',side_effect=sale.CheckoutUncertain('Check status')) as checkout, patch.object(sales.messagebox,'showerror'):
            frame._on_complete();frame._on_complete()
            self.assertEqual(checkout.call_count,1)
            self.assertTrue(frame._cart)
            frame._btn_complete.config.assert_called_with(state='disabled')

    def test_navigation_logout_and_search(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        import app
        frame=self.frame()
        frame._all_data=[dict(id=1,name='napa',generic='paracetamol',strength='500mg',price=Decimal('2.50'),stock=10,expires_date=sale.shop_now().date())]
        for query in ('napa','PARACETAMOL','500 mg','absent'):
            frame._search_var.set(query);frame._filter_medicines()
            self.assertEqual(len(frame._medicine_tree.rows),0 if query=='absent' else 1)
        frames={name:Mock() for name in ('LoginFrame','DashboardFrame','MedicineFrame','SupplierFrame')}
        frames['SalesFrame']=frame
        controller=SimpleNamespace(admin_username='Admin',frames=frames,shell=Mock(),_username_lbl=Mock(),_nav_buttons={name:Mock() for name in frames if name!='LoginFrame'})
        controller.show_frame=lambda name:app.App.show_frame(controller,name)
        identities={key:id(value) for key,value in frames.items()}
        for repeat in range(100):
            for name in ('DashboardFrame','SalesFrame','MedicineFrame','SupplierFrame','SalesFrame'):
                controller.show_frame(name)
        self.assertEqual(identities,{key:id(value) for key,value in frames.items()})
        self.assertEqual(controller.admin_username,'Admin')
        self.assertEqual(frame.refresh_medicines.call_count,200)
        frame._cart={1:dict(name='Napa',strength='500 mg',unit_price=Decimal('2.50'),quantity=2)}
        app.App.logout(controller)
        self.assertFalse(frame._cart);self.assertIsNone(controller.admin_username)

    def test_friendly_history_deletion_error(self):
        import medicine
        from unittest.mock import Mock
        from mysql.connector import IntegrityError
        cursor=Mock();cursor.execute.side_effect=IntegrityError('History restriction',errno=1451)
        connection=Mock();connection.cursor.return_value=cursor
        with patch.object(medicine,'conn',connection):
            with self.assertRaisesRegex(ValueError,'sales history'):
                medicine.delete_medicine(1)
        connection.rollback.assert_called_once();cursor.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
