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

from pydantic import BaseModel

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ Args:
        potions_delivered (List[PotionInventory]): A list of delivered PotionInventory objects.
        order_id (int): The order ID for the delivery.
    """
    with db.engine.begin() as connection:
        potion_totals = {'red': 0, 'green': 0, 'blue': 0, 'dark': 0}
        for potinv in potions_delivered:
            potion_type = potinv.potion_type
            quantity = potinv.quantity
            potion_totals['red'] += potion_type[0] * quantity
            potion_totals['green'] += potion_type[1] * quantity
            potion_totals['blue'] += potion_type[2] * quantity
            potion_totals['dark'] += potion_type[3] * quantity
            update_stocked_query = f"""UPDATE potions
                SET stocked = stocked + {quantity}
                WHERE typ = ARRAY{potion_type}"""
            connection.execute(sqlalchemy.text(update_stocked_query))
        
        update_ml_query = f"""UPDATE gl_inv
            SET num_green_ml = num_green_ml - {potion_totals['green']},
                num_red_ml = num_red_ml - {potion_totals['red']},
                num_blue_ml = num_blue_ml - {potion_totals['blue']},
                num_dark_ml = num_dark_ml - {potion_totals['dark']}"""
        connection.execute(sqlalchemy.text(update_ml_query))

        print(f"CALLED BOTTLES DELIVERY. order_id: {order_id}")
    for color, total in potion_totals.items():
        print(f"Total {color} ml used: {total}")
    return {"success": True}


@router.post("/plan")
def get_bottle_plan():
    """Decide which potions to order based on available ml in barrels."""
    with db.engine.begin() as connection:
        ml_query = "SELECT num_green_ml, num_red_ml, num_blue_ml, num_dark_ml FROM gl_inv"
        green_ml, red_ml, blue_ml, dark_ml = connection.execute(sqlalchemy.text(ml_query)).fetchone()
        potions = connection.execute(sqlalchemy.text("SELECT typ, norm FROM potions WHERE selling = TRUE ORDER BY lead DESC")).fetchall()
    
    available_ml = {"red": red_ml, "green": green_ml, "blue": blue_ml, "dark": dark_ml}
    potential_potions = []

    for potion in potions:
        typ_array, norm = potion
        can_make = all(available_ml[color] >= amount for color, amount in zip([ "red", "green", "blue", "dark"], typ_array) if amount > 0)
        if can_make:
            in_cart = 0
            potential_potions.append((typ_array, norm, in_cart))

    purchase_plan = []
    updated = True

    # Continue iterating through potential potions until no updates can be made
    while updated:
        updated = False
        for i in range(len(potential_potions)):
            typ_array, norm, in_cart = potential_potions[i]
            if norm > 0:
                can_buy = all(available_ml[color] >= amount for color, amount in zip([ "red", "green", "blue", "dark"], typ_array) if amount > 0)
                if can_buy:
                    for color, amount in zip(["red", "green", "blue", "dark"], typ_array):
                        if amount > 0:
                            available_ml[color] -= amount
                    potential_potions[i] = (typ_array, norm - 1, in_cart + 1)
                    updated = True

    for typ_array, norm, in_cart in potential_potions:
        if in_cart > 0:
            purchase_plan.append({"potion_type": typ_array, "quantity": in_cart})

    print(f"SENDING PURCHASE PLAN: {purchase_plan}")
    return purchase_plan



if __name__ == "__main__":
    print(get_bottle_plan())
