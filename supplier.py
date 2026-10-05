from db import conn


def add_supplier(name, contact_person, phone, email, address):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO suppliers (name, contact_person, phone, email, address)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, contact_person or None, phone, email or None, address or None))
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_all_suppliers():
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM suppliers ORDER BY id")
        return cursor.fetchall()
    finally:
        cursor.close()


def search_suppliers(query, rows=None):
    """Search cached rows for live typing, or load rows for standalone use."""
    if rows is None:
        rows = get_all_suppliers()
    query = query.strip().casefold()
    return [row for row in rows if any(query in (row.get(field) or "").casefold()
            for field in ("name", "contact_person", "phone"))]


def update_supplier(supplier_id, name, contact_person, phone, email, address):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE suppliers SET name=%s, contact_person=%s, phone=%s, email=%s, address=%s
            WHERE id=%s
        """, (name, contact_person or None, phone, email or None, address or None, supplier_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def delete_supplier(supplier_id):
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM suppliers WHERE id=%s", (supplier_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
