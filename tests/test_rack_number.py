"""Numeric rack regression checks; writes use a connection-local temporary table."""
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

import db
import medicine
import report
from sales import SalesFrame


class RackNumberTests(unittest.TestCase):
    def test_migration_only_adds_missing_column(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchall.return_value = [('generic',), ('strength',)]
        with patch.object(db, 'conn', connection):
            db.init_medicine_fields()
        self.assertEqual(cursor.execute.call_args_list[-1].args,
                         ('ALTER TABLE medicines ADD COLUMN `rack_number` INT NULL DEFAULT NULL',))
        cursor.reset_mock()
        cursor.fetchall.return_value = [('generic',), ('strength',), ('rack_number',)]
        with patch.object(db, 'conn', connection):
            db.init_medicine_fields()
        cursor.execute.assert_called_once_with('SHOW COLUMNS FROM medicines')
        cursor.close.assert_called_once()

    def test_crud_inventory_and_selection(self):
        cursor = db.conn.cursor()
        cursor.execute('SELECT * FROM medicines ORDER BY id')
        original = cursor.fetchall()
        db.conn.commit()
        cursor.execute('CREATE TEMPORARY TABLE medicines AS SELECT source.* FROM medicines source WHERE 1=0')
        cursor.execute('ALTER TABLE medicines MODIFY id INT NOT NULL AUTO_INCREMENT PRIMARY KEY')
        try:
            medicine.add_medicine('Rack test', Decimal('2.50'), 10, '2030-01-01',
                                  'Generic', '500 mg', "  1  ")
            row = medicine.get_all_medicines()[0]
            ident = row['id']
            self.assertEqual(row['rack_number'], 1)
            self.assertEqual(report.get_inventory_report()[0]['rack_number'], 1)
            frame = SalesFrame.__new__(SalesFrame)
            frame._selected_label = Mock()
            frame._btn_add = Mock()
            frame._show_selection(row)
            self.assertIn('Rack No.: 1', frame._selected_label.config.call_args.kwargs['text'])
            medicine.update_medicine(ident, 'Rack test', Decimal('2.50'), 10, '2030-01-01',
                                     'Generic', '500 mg', 2)
            self.assertEqual(medicine.get_medicine_by_id(ident)['rack_number'], 2)
            medicine.add_medicine('Shared rack', 1, 10, '2030-01-01', rack_number=1)
            self.assertEqual(medicine.get_all_medicines()[1]['rack_number'], 1)
            cursor.execute("INSERT INTO medicines (name,price,stock,expires_date) VALUES (%s,%s,%s,%s)",
                           ('Legacy', 1, 10, '2030-01-01'))
            db.conn.commit()
            legacy = medicine.get_all_medicines()[-1]
            self.assertIsNone(legacy['rack_number'])
            frame._show_selection(legacy)
            self.assertIn('Rack No.: Not assigned', frame._selected_label.config.call_args.kwargs['text'])
            medicine.update_medicine(legacy['id'], 'Legacy', 1, 10, '2030-01-01', rack_number=1)
            self.assertEqual(medicine.get_medicine_by_id(legacy['id'])['rack_number'], 1)
            for invalid in (None, '', '   ', 0, -1, '1.5', 'abc', True, 2147483648, '9' * 5000):
                with self.subTest(invalid=str(invalid)[:20]):
                    with self.assertRaises(ValueError):
                        medicine.add_medicine('Invalid', 1, 1, '2030-01-01', rack_number=invalid)
                    with self.assertRaises(ValueError):
                        medicine.update_medicine(ident, 'Invalid', 1, 1, '2030-01-01', rack_number=invalid)
            self.assertEqual(len(medicine.get_all_medicines()), 3)
            medicine.delete_medicine(ident)
            self.assertIsNone(medicine.get_medicine_by_id(ident))
        finally:
            cursor.execute('DROP TEMPORARY TABLE medicines')
            db.conn.commit()
            cursor.execute('SELECT * FROM medicines ORDER BY id')
            self.assertEqual(cursor.fetchall(), original)
            db.conn.commit()
            cursor.close()


if __name__ == '__main__':
    unittest.main()

