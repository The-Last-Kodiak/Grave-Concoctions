import sqlalchemy
from src import database as db
from fastapi import APIRouter


router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT sku, name, quantity, price, potion_type FROM potions WHERE potion_type[2] > 0"))
        
        potions = result.fetchall()
        catalog = [
            {
                "sku": row['sku'],
                "name": row['name'],
                "quantity": row['quantity'],
                "price": row['price'],
                "potion_type": row['potion_type'],
            }
            for row in potions
        ]
    return catalog
