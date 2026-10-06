"""Read-only report queries against the existing pharmacy tables."""
import re
from datetime import date, timedelta
from db import conn
from sale import shop_now

LOW_STOCK_THRESHOLD = 10
EXPIRING_DAYS = 30


def validate_dates(from_text="", to_text=""):
    dates = []
    for label, text in (("From Date", from_text), ("To Date", to_text)):
        text = text.strip()
        if not text:
            dates.append(None)
            continue
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
                raise ValueError
            dates.append(date.fromisoformat(text))
        except ValueError:
            raise ValueError(f"{label} must be a valid date in YYYY-MM-DD format.") from None
    start, end = dates
    if start and end and start > end:
        raise ValueError("From Date must not be after To Date.")
    return start, end


def _read(query, params=()):
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        # End the read transaction so subsequent refreshes see new checkout data,
        # matching the existing medicine/supplier read helpers.
        conn.commit()
        return rows
    finally:
        cursor.close()


def get_sales_report(from_text="", to_text=""):
    start, end = validate_dates(from_text, to_text)
    conditions, params = [], []
    if start:
        conditions.append("s.sale_date >= %s")
        params.append(start)
    if end:
        # The exclusive next-day boundary includes every time on To Date.
        if end == date.max:
            conditions.append("s.sale_date <= %s")
            params.append("9999-12-31 23:59:59.999999")
        else:
            conditions.append("s.sale_date < %s")
            params.append(end + timedelta(days=1))
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    return _read("""SELECT s.id, s.sale_date, a.username AS sold_by, s.total_amount
                    FROM sales s JOIN admins a ON a.id = s.sold_by""" + where +
                 " ORDER BY s.sale_date DESC, s.id DESC", tuple(params))


def get_sale_header(sale_id):
    rows = _read("""SELECT s.id, s.sale_date, a.username AS sold_by, s.total_amount
                    FROM sales s JOIN admins a ON a.id = s.sold_by
                    WHERE s.id = %s""", (sale_id,))
    return rows[0] if rows else None


def get_sale_details(sale_id):
    return _read("""SELECT m.name, m.strength, si.quantity, si.unit_price, si.subtotal
                    FROM sales s JOIN sale_items si ON si.sale_id = s.id
                    JOIN medicines m ON m.id = si.medicine_id
                    WHERE s.id = %s ORDER BY si.id""", (sale_id,))


def get_inventory_report():
    return _read("""SELECT id, name, generic, strength, stock, price, expires_date
                    FROM medicines ORDER BY name, id""")


def get_alert_report():
    today = shop_now().date()
    cutoff = today + timedelta(days=EXPIRING_DAYS)
    rows = _read("""SELECT id, name, strength, stock, expires_date FROM medicines
                    WHERE stock <= %s OR expires_date <= %s ORDER BY name, id""",
                 (LOW_STOCK_THRESHOLD, cutoff))
    for row in rows:
        statuses = []
        if row["stock"] <= LOW_STOCK_THRESHOLD:
            statuses.append("Low Stock")
        expiry = row["expires_date"]
        if expiry and expiry < today:
            statuses.append("Expired")
        elif expiry and today <= expiry <= cutoff:
            statuses.append("Expiring Soon")
        row["status"] = ", ".join(statuses)
    return rows
