import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import itertools
from src.api.inventory import update_gold, get_current_gold, update_potion_inventory, get_current_potion_inventory, update_ml, get_current_ml


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
    potion_totals = {'red': 0, 'green': 0, 'blue': 0, 'dark': 0}
    type_str = ['red', 'green', 'blue', 'dark']
    for potinv in potions_delivered:
        potion_type = potinv.potion_type
        quantity = potinv.quantity
        query = "SELECT sku FROM potions WHERE typ = :potion_type LIMIT 1"
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text(query), {"potion_type": potion_type}).fetchone()
        sku = result[0] if result else None
        if not sku:
            continue  # Skip if no matching SKU is found
        for i, amount in enumerate(potion_type):
            if amount > 0:
                potion_totals[type_str[i]] += amount * quantity
                update_potion_inventory(sku, quantity)
    for color, total in potion_totals.items():
        if total > 0:
            update_ml(color.upper(), -total)
            print(f"Total {color} ml used: {total}")
    print(f"CALLED BOTTLES DELIVERY. order_id: {order_id}")
    return "OK"



@router.post("/plan")
def get_bottle_plan():
    green_ml = get_current_ml("GREEN") or 0
    red_ml = get_current_ml("RED") or 0
    blue_ml = get_current_ml("BLUE") or 0
    dark_ml = get_current_ml("DARK") or 0
    
    available_ml = {"red": red_ml, "green": green_ml, "blue": blue_ml, "dark": dark_ml}
    potential_potions = []
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT typ, norm FROM potions WHERE selling = TRUE ORDER BY lead DESC")).fetchall()
    for potion in potions:
        typ_array, norm = potion
        can_make = all(available_ml[color] >= amount for color, amount in zip(["red", "green", "blue", "dark"], typ_array) if amount > 0)
        if can_make:
            in_cart = 0
            potential_potions.append((typ_array, norm, in_cart))
    purchase_plan = []
    updated = True
    while updated:
        updated = False
        for i in range(len(potential_potions)):
            typ_array, norm, in_cart = potential_potions[i]
            if norm > 0:
                can_buy = all(available_ml[color] >= amount for color, amount in zip(["red", "green", "blue", "dark"], typ_array) if amount > 0)
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
