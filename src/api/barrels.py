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
    
    # Mapping potion types to their corresponding attributes
    potion_types = {
        "green": {"sku": "", "cost": float('inf'), "needed": 0, "potion_qry": "SELECT num_green_potions FROM global_inventory"},
        "blue": {"sku": "", "cost": float('inf'), "needed": 0, "potion_qry": "SELECT num_blue_potions FROM global_inventory"},
        "red": {"sku": "", "cost": float('inf'), "needed": 0, "potion_qry": "SELECT num_red_potions FROM global_inventory"}
        }

    # Identify the lowest cost barrels for each potion type
    for barrel in wholesale_catalog:
        potion_type = None
        if barrel.potion_type[1] == 1:
            potion_type = "green"
        elif barrel.potion_type[2] == 1:
            potion_type = "blue"
        elif barrel.potion_type[0] == 1:
            potion_type = "red"
        
        if potion_type and barrel.price < potion_types[potion_type]["cost"]:
            potion_types[potion_type]["sku"] = barrel.sku
            potion_types[potion_type]["cost"] = barrel.price
    
    # Fetch the current inventory and gold
    gold_qry = "SELECT gold FROM global_inventory"
    with db.engine.begin() as connection:
        for potion in potion_types:
            potion_types[potion]["current"] = connection.execute(sqlalchemy.text(potion_types[potion]["potion_qry"])).scalar()
        gold = connection.execute(sqlalchemy.text(gold_qry)).scalar()

    # Purchase logic
    while gold > 0:
        # Find the potion type with the least inventory
        min_potion = min(potion_types, key=lambda x: potion_types[x]["current"])
        min_cost = potion_types[min_potion]["cost"]

        if gold >= min_cost and potion_types[min_potion]["current"] < 10:
            gold -= min_cost
            potion_types[min_potion]["needed"] += 1
            potion_types[min_potion]["current"] += 1
        else:
            break
    
    purchase_plan = [
        {"sku": potion_types[potion]["sku"], "quantity": potion_types[potion]["needed"]}
        for potion in potion_types if potion_types[potion]["needed"] > 0
    ]

    return purchase_plan
    

    purchase_plan = [
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
    # Filter out barrels with quantity <= 0
    return [barrel for barrel in purchase_plan if barrel["quantity"] > 0]
