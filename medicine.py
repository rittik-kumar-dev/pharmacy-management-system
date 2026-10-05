from db import conn

def add_medicine(name,price ,stock,expires_date,generic=None,strength=None):
    cursor=conn.cursor() # cursor is truck which carry query, conn is bridge to mysql
    query="""
    INSERT INTO medicines(name,price,stock,expires_date,generic,strength)
    VALUES(%s,%s,%s,%s,%s,%s)   
    """
    #%s means placeholders, which is empty
    # Using placeholders prevents SQL Injection means security risk
    values=(name,price,stock,expires_date,generic or None,strength or None)
    
    cursor.execute(query,values)  # curson run it on mysql server and take data into it(cursor)
    conn.commit() # save data in mysql
    cursor.close()
    
    print("Medicine Added Successfully")
    
    
def get_all_medicines():
    cursor=conn.cursor(dictionary=True) # it take data as dictionary format
    try:
        cursor.execute("SELECT * FROM medicines")
        return cursor.fetchall() #fetch data from cursor
    finally:
        cursor.close()
    
   
   
def get_medicine_by_id(one_id):
    cursor=conn.cursor(dictionary=True)
    query="SELECT * FROM medicines WHERE id=%s "
    try:
        cursor.execute(query, (one_id,)) # one_id has to be sent as a Tuple(,)|and use a , for single one value
        return cursor.fetchone()
    finally:
        cursor.close()
    
    
    
def update_medicine(one_id,name,price,stock,expires_date,generic=None,strength=None):
         cursor=conn.cursor(dictionary=True)
         query="""
         UPDATE medicines 
         SET name=%s,price=%s,stock=%s,expires_date=%s,generic=%s,strength=%s
         WHERE id=%s
         """
         values=(name,price,stock,expires_date,generic or None,strength or None,one_id)
         cursor.execute(query,values)
         conn.commit()
         print(f"update {one_id} successfully")
         cursor.close()
         
def delete_medicine(one_id)   :
    cursor=conn.cursor(dictionary=True)
    query="""
    DELETE FROM medicines WHERE id=%s
    """
    cursor.execute(query,(one_id,))
    conn.commit()
    cursor.close()
    
          
         
         
          
        
       
         
          
    
