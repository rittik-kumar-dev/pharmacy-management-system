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