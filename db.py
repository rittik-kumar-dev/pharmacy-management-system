import mysql.connector
try:
    conn=mysql.connector.connect(
        host="localhost",
        user="root",
        password="#Rittik123",
        database="pharmacy"
    )
    print("Database Connected successfully")

except Exception as e:
    print("error:",e)    
    

def init_admin_table():
    """
    Creates the 'admins' table if it doesn't already exist.
    Runs once at startup so you never have to manually create it in MySQL Workbench.
    """
    cursor = conn.cursor()
    query = """
    CREATE TABLE IF NOT EXISTS admins (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    cursor.execute(query)
    conn.commit()
    cursor.close()


# Run it as soon as db.py is imported anywhere in the project,
# so the table always exists before login.py or auth.py needs it.
init_admin_table()

def init_medicine_fields():
    """Add optional medicine details without changing existing records."""
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW COLUMNS FROM medicines")
        columns = {row[0] for row in cursor.fetchall()}
        for field in ("generic", "strength"):
            if field not in columns:
                cursor.execute(
                    f"ALTER TABLE medicines ADD COLUMN `{field}` VARCHAR(100) NULL DEFAULT NULL"
                )
        conn.commit()
    finally:
        cursor.close()


init_medicine_fields()


def init_suppliers_table():
    """Create suppliers without replacing any existing table or records."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                contact_person VARCHAR(100),
                phone VARCHAR(20) NOT NULL,
                email VARCHAR(100),
                address VARCHAR(255)
            )
        """)
        conn.commit()
    finally:
        cursor.close()


init_suppliers_table()


def init_sales_tables():
    """Add sales history without replacing existing tables or data."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sale_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                total_amount DECIMAL(10,2) NOT NULL,
                sold_by INT NOT NULL,
                INDEX idx_sales_date (sale_date),
                CONSTRAINT chk_sales_total CHECK (total_amount > 0),
                CONSTRAINT fk_sales_admin FOREIGN KEY (sold_by) REFERENCES admins(id)
                    ON DELETE RESTRICT ON UPDATE RESTRICT
            ) ENGINE=InnoDB
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sale_id INT NOT NULL,
                medicine_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                subtotal DECIMAL(10,2) NOT NULL,
                UNIQUE KEY uq_sale_medicine (sale_id, medicine_id),
                CONSTRAINT chk_sale_item_quantity CHECK (quantity > 0),
                CONSTRAINT chk_sale_item_price CHECK (unit_price > 0),
                CONSTRAINT chk_sale_item_subtotal CHECK (subtotal = quantity * unit_price),
                CONSTRAINT fk_sale_items_sale FOREIGN KEY (sale_id) REFERENCES sales(id)
                    ON DELETE RESTRICT ON UPDATE RESTRICT,
                CONSTRAINT fk_sale_items_medicine FOREIGN KEY (medicine_id) REFERENCES medicines(id)
                    ON DELETE RESTRICT ON UPDATE RESTRICT
            ) ENGINE=InnoDB
        """)
        conn.commit()
    finally:
        cursor.close()


init_sales_tables()
