import re
import sqlalchemy
from src import database as db
from fastapi import APIRouter


router = APIRouter()

qry = "SELECT gold FROM global_inventory"

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(qry)).scalar()
    return result
    return [
            {
                "sku": "GREEN_POTION_0",
                "name": "red potion",
                "quantity": 1,
                "price": 50,
                "potion_type": [100, 0, 0, 0],
            }
        ]
