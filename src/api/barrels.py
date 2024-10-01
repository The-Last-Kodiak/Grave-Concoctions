import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth


router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int
    potion_type: list[int]
    price: int
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            result = connection.execute(sqlalchemy.text("""
                INSERT INTO barrels (order_id, sku, ml_per_barrel, potion_type, price, quantity)
                VALUES (:order_id, :sku, :ml_per_barrel, :potion_type, :price, :quantity)
                ON CONFLICT (order_id, sku) DO UPDATE
                SET quantity = barrels.quantity + EXCLUDED.quantity
            """), {
                "order_id": order_id,
                "sku": barrel.sku,
                "ml_per_barrel": barrel.ml_per_barrel,
                "potion_type": barrel.potion_type,
                "price": barrel.price,
                "quantity": barrel.quantity
            })
    #print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")
    
    return 0

# Gets called once a day

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """
    Gets the plan for purchasing wholesale barrels.
    The call passes in a catalog of available barrels and the shop 
    returns back which barrels they'd like to purchase and how many.
    """
    purchase_plan = []

    # Example logic: Purchase one barrel of each type if the quantity is less than 10
    for barrel in wholesale_catalog:
        if barrel.potion_type[1] == 1:  # Assuming potion_type[1] represents green potions
            with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text("""
                    SELECT SUM(quantity) as total_quantity
                    FROM barrels
                    WHERE potion_type[2] > 0
                """))
                total_quantity = result.fetchone()['total_quantity']
                
                if total_quantity < 10:
                    purchase_plan.append({
                        "sku": barrel.sku,
                        "quantity": min(1, barrel.quantity)  # Purchase at least 1, but not more than available
                    })

    return purchase_plan
    #{"sku": "SMALL_GREEN_BARREL","quantity": 1,}

