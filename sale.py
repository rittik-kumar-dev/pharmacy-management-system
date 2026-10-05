"""Cart validation and atomic checkout; no Tkinter dependencies."""
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from db import conn

MAX_AMOUNT = Decimal("99999999.99")
SHOP_TIMEZONE = timezone(timedelta(hours=6))


class SaleError(ValueError):
    pass


class PriceChanged(SaleError):
    def __init__(self, prices):
        super().__init__("Medicine prices have changed. Review the updated cart total before completing the sale.")
        self.prices = prices


class CheckoutUncertain(SaleError):
    pass


def shop_now():
    return datetime.now(SHOP_TIMEZONE).replace(tzinfo=None)


def purchase_quantity(value):
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]+", text):
        raise SaleError("Quantity must be a positive whole number.")
    text = text.lstrip("0") or "0"
    if len(text) > 10 or not 1 <= int(text) <= 2147483647:
        raise SaleError("Quantity must be a positive whole number no greater than 2147483647.")
    return int(text)


def money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
            raise ValueError
        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError
        return amount
    except (InvalidOperation, ValueError):
        raise SaleError("Medicine price must be a valid positive amount with at most two decimal places.")


def validate_medicine(medicine, quantity, today=None):
    if medicine is None:
        raise SaleError("This medicine no longer exists. Remove it from the cart.")
    today = today or shop_now().date()
    expiry = medicine.get("expires_date")
    if not isinstance(expiry, date):
        raise SaleError("This medicine has no valid expiry date and cannot be sold.")
    if expiry < today:
        raise SaleError("This medicine has expired and cannot be sold.")
    quantity = purchase_quantity(quantity)
    if medicine["stock"] <= 0:
        raise SaleError("This medicine is out of stock.")
    if quantity > medicine["stock"]:
        raise SaleError("Quantity exceeds available stock.")
    price = money(medicine["price"])
    if price * quantity > MAX_AMOUNT:
        raise SaleError("Sale amount exceeds the supported limit of 99999999.99.")
    return price


def add_to_cart(cart, medicine, quantity):
    quantity = purchase_quantity(quantity)
    existing = cart.get(medicine["id"])
    combined = quantity + (existing["quantity"] if existing else 0)
    price = validate_medicine(medicine, combined)
    if existing and existing["unit_price"] != price:
        raise PriceChanged({medicine["id"]: price})
    subtotal = price * combined
    total = sum((item["unit_price"] * item["quantity"] for key, item in cart.items()
                 if key != medicine["id"]), Decimal("0.00")) + subtotal
    if total > MAX_AMOUNT:
        raise SaleError("Sale amount exceeds the supported limit of 99999999.99.")
    cart[medicine["id"]] = dict(medicine_id=medicine["id"], name=medicine["name"],
                               strength=medicine.get("strength") or "",
                               quantity=combined, unit_price=price)


def complete_sale(username, cart):
    if not username or not username.strip():
        raise SaleError("Please log in before completing a sale.")
    if not cart:
        raise SaleError("Add at least one medicine to the cart.")
    # The single-threaded UI commits every write. End an outstanding read snapshot.
    conn.rollback()
    conn.start_transaction()
    cursor = None
    committing = False
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM admins WHERE username=%s", (username.strip(),))
        admin = cursor.fetchone()
        if admin is None:
            raise SaleError("The logged-in admin no longer exists. Please log in again.")
        checked = []
        changed_prices = {}
        for medicine_id in sorted(cart):
            item = cart[medicine_id]
            quantity = purchase_quantity(item["quantity"])
            cursor.execute("SELECT * FROM medicines WHERE id=%s FOR UPDATE", (medicine_id,))
            medicine = cursor.fetchone()
            price = validate_medicine(medicine, quantity)
            if price != money(item["unit_price"]):
                changed_prices[medicine_id] = price
            checked.append((medicine_id, quantity, price, price * quantity))
        if changed_prices:
            raise PriceChanged(changed_prices)
        total = sum((row[3] for row in checked), Decimal("0.00"))
        if total > MAX_AMOUNT:
            raise SaleError("Sale amount exceeds the supported limit of 99999999.99.")
        cursor.execute("INSERT INTO sales (sale_date,total_amount,sold_by) VALUES (%s,%s,%s)",
                       (shop_now(), total, admin["id"]))
        sale_id = cursor.lastrowid
        for medicine_id, quantity, price, subtotal in checked:
            cursor.execute("""INSERT INTO sale_items
                (sale_id,medicine_id,quantity,unit_price,subtotal) VALUES (%s,%s,%s,%s,%s)""",
                (sale_id, medicine_id, quantity, price, subtotal))
            cursor.execute("UPDATE medicines SET stock=stock-%s WHERE id=%s AND stock>=%s",
                           (quantity, medicine_id, quantity))
            if cursor.rowcount != 1:
                raise SaleError("Stock changed. Refresh availability and try again.")
        committing = True
        conn.commit()
        return sale_id
    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass
        if committing:
            raise CheckoutUncertain("Checkout confirmation failed. The sale may have been saved. Do not retry until its status is checked in MySQL.") from error
        raise
    finally:
        if cursor is not None:
            cursor.close()
