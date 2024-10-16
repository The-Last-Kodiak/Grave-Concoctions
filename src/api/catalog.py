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
    green_qry = "SELECT num_green_potions FROM gl_inv"
    blue_qry = "SELECT num_blue_potions FROM gl_inv"
    red_qry = "SELECT num_red_potions FROM gl_inv"
    with db.engine.begin() as connection:
        green_potions = connection.execute(sqlalchemy.text(green_qry)).scalar()
        blue_potions = connection.execute(sqlalchemy.text(blue_qry)).scalar()
        red_potions = connection.execute(sqlalchemy.text(red_qry)).scalar()
    
    cata_diction = []
    if green_potions > 1:
        cata_diction.append({
            "sku": "GREEN_CONCOCTION",
            "name": "green concoction",
            "quantity": green_potions,
            "price": 50,
            "potion_type": [0, 100, 0, 0]
        })
    if blue_potions > 1:
        cata_diction.append({
            "sku": "BLUE_CONCOCTION",
            "name": "blue concoction",
            "quantity": blue_potions,
            "price": 50,
            "potion_type": [0, 0, 100, 0]
        })
    if red_potions > 1:
        cata_diction.append({
            "sku": "RED_CONCOCTION",
            "name": "red concoction",
            "quantity": red_potions,
            "price": 50,
            "potion_type": [100, 0, 0, 0]
        })
    #remeber to update sku's in carts
    print(f"CALLED CATALOG: {cata_diction}")
    return cata_diction

