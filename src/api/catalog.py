import re
import sqlalchemy
from src import database as db
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

"""
class Item(BaseModel):
    sku: str
    name: str
    quantity: int
    price: int
    potion_type: list[int]
"""

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """Each unique item combination must have only a single price."""
    query = "SELECT sku, price, stocked, typ FROM potions WHERE stocked > 0 AND selling = TRUE"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(query)).fetchall()
    cata_diction = []
    for row in result:
        cata_diction.append({
            "sku": row[0],
            "name": row[0].replace("_", " ").title(),  # Converting SKU to a more readable name
            "quantity": row[2],
            "price": row[1],
            "potion_type": row[3]
        })
    #remeber to update sku's in carts
    print(f"CALLED CATALOG: {cata_diction}")
    return cata_diction

