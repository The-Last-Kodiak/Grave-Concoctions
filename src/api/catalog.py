import re
import sqlalchemy
from src import database as db
from fastapi import APIRouter


router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    potions_qry = "SELECT num_green_potions FROM global_inventory"
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text(potions_qry)).scalar()
    return [
            {
                "sku": "GREEN_POTION_CONCOCTION",
                "name": "green concoction",
                "quantity": potions,
                "price": 50,
                "potion_type": [0, 100, 0, 0],
            }
        ]
