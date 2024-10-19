import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import itertools


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
    """ Args: potions_delivered (List[PotionInventory]): A list of delivered PotionInventory objects.
              order_id (int): The order ID for the delivery."""
    with db.engine.begin() as connection:
        potion_totals = {}
        for potinv in potions_delivered:
            potion_type_key = tuple(potinv.potion_type)
            potion_totals[potion_type_key] = potinv.quantity

        for potion_type, total_quantity in potion_totals.items():
            typ_str = ', '.join(map(str, potion_type))
            connection.execute(sqlalchemy.text(f"""
                UPDATE potions
                SET stocked = stocked + {total_quantity}
                WHERE typ = ARRAY[{typ_str}]::integer[];"""))
    print(f"CALLED BOTTLES DELIVERY. order_id: {order_id}")
    for potion_type, total_quantity in potion_totals.items():
        print(f"Type: {potion_type}, Quantity: {total_quantity}")
    return {"success": True}


@router.post("/plan")
def get_bottle_plan():
    """Decide which potions to order based on available ml in barrels."""
    with db.engine.begin() as connection:
        ml_query = "SELECT num_green_ml, num_red_ml, num_blue_ml, num_dark_ml FROM gl_inv"
        green_ml, red_ml, blue_ml, dark_ml = connection.execute(sqlalchemy.text(ml_query)).fetchone()
        potions_query = "SELECT typ, stocked FROM potions WHERE selling = TRUE "
        potions = connection.execute(sqlalchemy.text(potions_query)).fetchall()
    available_ml = {"green": green_ml, "red": red_ml, "blue": blue_ml, "dark": dark_ml}
    potential_potions = []
    for potion in potions:
        typ_array, stocked = potion
        potential_potions.append((typ_array, stocked))
    def potion_efficiency(potion):
        typ_array, _ = potion
        return sum(typ_array) / max(1, min(available_ml[color] // amount for color, amount in zip(["green", "red", "blue", "dark"], typ_array) if amount > 0))
    potential_potions.sort(key=potion_efficiency)
    purchase_plan = []
    total_potions = 0
    for typ_array, stocked in potential_potions:
        actual_order_quantity = min(
            available_ml[color] // amount for color, amount in zip(["green", "red", "blue", "dark"], typ_array) if amount > 0)
        if actual_order_quantity > 0:
            for color, amount in zip(["green", "red", "blue", "dark"], typ_array):
                if amount > 0:
                    available_ml[color] -= actual_order_quantity * amount
            purchase_plan.append({"potion_type": typ_array, "quantity": actual_order_quantity})
            total_potions += actual_order_quantity
    with db.engine.begin() as connection:
        update_ml_query = f"""UPDATE gl_inv 
            SET num_green_ml = {available_ml["green"]}, 
                num_red_ml = {available_ml["red"]}, 
                num_blue_ml = {available_ml["blue"]}, 
                num_dark_ml = {available_ml["dark"]}"""
        connection.execute(sqlalchemy.text(update_ml_query))
    print(f"SENDING PURCHASE PLAN: {purchase_plan}")
    return purchase_plan
    
if __name__ == "__main__":
    print(get_bottle_plan())
