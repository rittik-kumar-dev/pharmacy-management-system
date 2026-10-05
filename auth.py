from db import conn
import bcrypt
import mysql.connector

# ─── Why bcrypt? ───────────────────────────────────────────────────
# Never store passwords as plain text in the database.
# bcrypt.hashpw() turns "mypassword123" into something like:
#   $2b$12$KIXaB3n6f8m0eZ...   (this is called a "hash")
# It also adds a random "salt" automatically, so even two admins
# with the same password get different hashes in the database.
# bcrypt.checkpw() re-hashes the typed password with the same salt
# and compares — it never needs to "decrypt" anything.


def admin_exists():
    """Returns True if at least one admin account exists."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM admins")
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0


def create_admin(username, password):
    """
    Creates a new admin account with a securely hashed password.
    Raises ValueError if the username is empty or already taken.
    """
    username = username.strip()
    if not username or not password:
        raise ValueError("Username and password cannot be empty.")

    password_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

    cursor = conn.cursor()
    try:
        query = "INSERT INTO admins (username, password_hash) VALUES (%s, %s)"
        cursor.execute(query, (username, hashed.decode("utf-8")))
        conn.commit()
    except mysql.connector.IntegrityError:
        raise ValueError(f"Username '{username}' is already taken.")
    finally:
        cursor.close()


def verify_admin(username, password):
    """
    Checks username + password against the database.
    Returns True if they match, False otherwise.
    """
    username = username.strip()
    if not username or not password:
        return False

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password_hash FROM admins WHERE username = %s", (username,))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return False  # no such admin

    stored_hash = row["password_hash"].encode("utf-8")
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash)