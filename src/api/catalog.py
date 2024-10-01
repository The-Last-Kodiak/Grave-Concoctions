import sqlalchemy
from src import database as db
from fastapi import APIRouter


router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Retrieves the catalog of items. Each unique item combination 
    should have only a single price.
    You can have at most 6 potion SKUs 
    offered in your catalog at one time.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT sku, name, quantity, price, potion_type
            FROM potions
            WHERE potion_type[2] > 0
            LIMIT 6
        """))
        
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
        
        # Validate and format the catalog
        validated_catalog = []
        for item in catalog:
            if (1 <= item['quantity'] <= 10000 and
                1 <= item['price'] <= 500 and
                sum(item['potion_type']) == 100 and
                re.match(r'^[a-zA-Z0-9_]{1,20}$', item['sku'])):
                validated_catalog.append(item)
        
    return validated_catalog
