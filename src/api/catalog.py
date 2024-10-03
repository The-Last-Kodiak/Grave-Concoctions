import re
import sqlalchemy
from src import database as db
from fastapi import APIRouter


router = APIRouter()

gold_qry = "SELECT gold FROM global_inventory"
potions_qry = "SELECT num_green_potions FROM global_inventory"
ml_qry = "SELECT num_green_ml FROM global_inventory"

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text(gold_qry)).scalar()
        potions = connection.execute(sqlalchemy.text(potions_qry)).scalar()
        ml = connection.execute(sqlalchemy.text(ml_qry)).scalar()
    return [
            {
                "sku": "GREEN_POTION_CONCOCTION",
                "name": "green concoction",
                "quantity": potions,
                "price": 50,
                "potion_type": [0, 100, 0, 0],
            }
        ]
