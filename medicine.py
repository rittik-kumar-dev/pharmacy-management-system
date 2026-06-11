from db import conn

def add_medicine(name,price ,stock,expires_date):
    cursor=conn.cursor() # cursor is truck which carry query, conn is bridge to mysql
    query="""
    INSERT INTO medicines(name,price,stock,expires_date)
    VALUES(%s,%s,%s,%s) # %s means placeholders, which is empty
    """
    values=(name,price,stock,expires_date)
    
    cursor.execute(query,values)  # curson run it on mysql server and take data into it(cursor)
    conn.commit() # save data in mysql
    cursor.close()
    
    print("Medicine Added Successfully")
    
    
def get_all_medicines():
    cursor=conn.cursor(dictionary=True) # it take data as dictionary format
    cursor.execute("SELECT * FROM medicines")
    return cursor.fetchall() #fetch data from cursor