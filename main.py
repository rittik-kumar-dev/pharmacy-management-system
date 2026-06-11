#from medicine import add_medicine
#add_medicine("Napa",5,100,"2026-10-6")
from medicine import get_all_medicines
medicines=get_all_medicines()
for med in medicines:
    
    name = med['name']
    price = med['price']
    stock = med['stock']
    expiry = med['expires_date']
    print(f"Name:{name}| price:{price} | stock:{stock}| expiry: {expiry}")
