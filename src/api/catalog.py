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

    green_qry = "SELECT num_green_potions FROM global_inventory"
    blue_qry = "SELECT num_blue_potions FROM global_inventory"
    red_qry = "SELECT num_red_potions FROM global_inventory"
    with db.engine.begin() as connection:
        green_potions = connection.execute(sqlalchemy.text(green_qry)).scalar()
        blue_potions = connection.execute(sqlalchemy.text(blue_qry)).scalar()
        red_potions = connection.execute(sqlalchemy.text(red_qry)).scalar()
    cata_diction = [
    {
        "sku": "GREEN_POTION_CONCOCTION",
        "name": "green concoction",
        "quantity": green_potions,
        "price": 50,
        "potion_type": [0, 100, 0, 0],
    },
    {
        "sku": "BLUE_POTION_CONCOCTION",
        "name": "blue concoction",
        "quantity": blue_potions,
        "price": 50,
        "potion_type": [0, 0, 100, 0],
    },
    {
        "sku": "RED_POTION_CONCOCTION",
        "name": "red concoction",
        "quantity": red_potions,
        "price": 50,
        "potion_type": [100, 0, 0, 0],
    }]
    print(cata_diction)
    return cata_diction
