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
    ml_qry = "SELECT num_green_ml FROM global_inventory"
    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text(gold_qry)).scalar()
        current_ml = connection.execute(sqlalchemy.text(ml_qry)).scalar()
    for barrel in barrels_delivered:
        if barrel.potion_type[1] == 1:
            current_ml += barrel.quantity*barrel.ml_per_barrel
            current_gold -= barrel.price*barrel.quantity
    new_ml_qry = f"UPDATE global_inventory SET num_green_ml = {current_ml}"
    new_gold_qry = f"UPDATE global_inventory SET gold = {current_gold}"
    with db.engine.begin() as connection:
        update1 = connection.execute(sqlalchemy.text(new_ml_qry))
        update2 = connection.execute(sqlalchemy.text(new_gold_qry))
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
    barrels_needed = 0
    green_barrel_cost = 0
    green_barrel_sku = ""
    potions_qry = "SELECT num_green_potions FROM global_inventory"
    gold_qry = "SELECT num_green_potions FROM global_inventory"
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text(potions_qry)).scalar()
        gold = connection.execute(sqlalchemy.text(gold_qry)).scalar()
    for barrel in wholesale_catalog: 
        if barrel.potion_type[1] == 1:
            green_barrel_sku = barrel.sku
            green_barrel_cost = barrel.price
    if potions < 10:
        if gold >= green_barrel_cost:
            barrels_needed += 1
    
    return [
        {
            "sku": green_barrel_sku,
            "quantity": barrels_needed,
        }
    ]

