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