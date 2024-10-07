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
    gold_qry = "SELECT gold FROM global_inventory"
    g_qry = "SELECT num_green_ml FROM global_inventory"
    r_qry = "SELECT num_red_ml FROM global_inventory"
    b_qry = "SELECT num_blue_ml FROM global_inventory"
    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text(gold_qry)).scalar()
        current_gml = connection.execute(sqlalchemy.text(g_qry)).scalar()
        current_rml = connection.execute(sqlalchemy.text(r_qry)).scalar()
        current_bml = connection.execute(sqlalchemy.text(b_qry)).scalar()
    for barrel in barrels_delivered:
        if barrel.potion_type[1] == 1:
            current_gml += barrel.quantity*barrel.ml_per_barrel
            current_gold -= barrel.price*barrel.quantity
        if barrel.potion_type[0] == 1:
            current_rml += barrel.quantity*barrel.ml_per_barrel
            current_gold -= barrel.price*barrel.quantity
        if barrel.potion_type[2] == 1:
            current_bml += barrel.quantity*barrel.ml_per_barrel
            current_gold -= barrel.price*barrel.quantity
    new_gml_qry = f"UPDATE global_inventory SET num_green_ml = {current_gml}"
    new_rml_qry = f"UPDATE global_inventory SET num_red_ml = {current_rml}"
    new_bml_qry = f"UPDATE global_inventory SET num_blue_ml = {current_bml}"
    new_gold_qry = f"UPDATE global_inventory SET gold = {current_gold}"
    with db.engine.begin() as connection:
        update1 = connection.execute(sqlalchemy.text(new_gml_qry))
        update2 = connection.execute(sqlalchemy.text(new_gold_qry))
        update3 = connection.execute(sqlalchemy.text(new_rml_qry))
        update4 = connection.execute(sqlalchemy.text(new_bml_qry))
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")
    
    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """
    Generates a wholesale purchase plan based on the current inventory of green potions.
    Args:
        wholesale_catalog (List[Barrel]): A list of Barrel objects representing the wholesale catalog.
    """
    barrels_dictionary = {barrel.sku: barrel for barrel in wholesale_catalog}
    
    green_barrels_needed = 0
    blue_barrels_needed = 0
    red_barrels_needed = 0
    green_barrel_sku = ""
    red_barrel_sku = ""
    blue_barrel_sku = ""
    green_barrel_cost = float('inf')
    red_barrel_cost = float('inf')
    blue_barrel_cost = float('inf')

    for barrel in wholesale_catalog: 
        if barrel.potion_type[1] == 1:
            green_barrel_sku = barrel.sku
            green_barrel_cost = barrel.price
        elif barrel.potion_type[2] == 1:
            blue_barrel_sku = barrel.sku
            blue_barrel_cost = barrel.price
        elif barrel.potion_type[0] == 1:
            red_barrel_sku = barrel.sku
            red_barrel_cost = barrel.price
    
    green_qry = "SELECT num_green_potions FROM global_inventory"
    red_qry = "SELECT num_red_potions FROM global_inventory"
    blue_qry = "SELECT num_blue_potions FROM global_inventory"
    gold_qry = "SELECT gold FROM global_inventory"
    with db.engine.begin() as connection:
        green_potions = connection.execute(sqlalchemy.text(green_qry)).scalar()
        red_potions = connection.execute(sqlalchemy.text(red_qry)).scalar()
        blue_potions = connection.execute(sqlalchemy.text(blue_qry)).scalar()
        gold = connection.execute(sqlalchemy.text(gold_qry)).scalar()
    
    if green_potions < 10:
        if gold >= green_barrel_cost:
            green_barrels_needed += 1
            gold -= green_barrel_cost
    if blue_potions < 10:
        if gold >= blue_barrel_cost:
            blue_barrels_needed += 1
            gold -= blue_barrel_cost
    if red_potions < 10:
        if gold >= red_barrel_cost:
            red_barrels_needed += 1
            gold -= red_barrel_cost

    return [
        {
            "sku": green_barrel_sku,
            "quantity": green_barrels_needed,
        },
        {
            "sku": red_barrel_sku,
            "quantity": red_barrels_needed,
        },
        {
            "sku": blue_barrel_sku,
            "quantity": blue_barrels_needed,
        }
    ]

