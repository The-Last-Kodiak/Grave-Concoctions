import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth


router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    with db.engine.begin() as connection:
        for potion in potions_delivered:
            result = connection.execute(sqlalchemy.text("""
                SELECT quantity
                FROM potions
                WHERE potion_type = :potion_type
            """), {
                "potion_type": potion.potion_type
            })
            available_quantity = result.fetchone()['quantity']
            
            if available_quantity >= potion.quantity:
                # Update the inventory
                connection.execute(sqlalchemy.text("""
                    UPDATE potions
                    SET quantity = quantity + :quantity
                    WHERE potion_type = :potion_type
                """), {
                    "quantity": potion.quantity,
                    "potion_type": potion.potion_type
                })
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT potion_type, SUM(quantity) as total_quantity
            FROM potions
            WHERE potion_type[2] > 0
            GROUP BY potion_type
        """))
        potions = result.fetchall()
        bottle_plan = []
        for row in potions:
            potion_type = row['potion_type']
            total_quantity = row['total_quantity']
            if potion_type[2] > 0 and total_quantity > 0:
                bottle_plan.append({
                    "potion_type": potion_type,
                    "quantity": total_quantity
                })
    return bottle_plan

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

if __name__ == "__main__":
    print(get_bottle_plan())

