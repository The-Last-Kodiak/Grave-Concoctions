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
    gold_qry = "SELECT gold FROM gl_inv"
    g_qry = "SELECT num_green_ml FROM gl_inv"
    r_qry = "SELECT num_red_ml FROM gl_inv"
    b_qry = "SELECT num_blue_ml FROM gl_inv"
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
    new_gml_qry = f"UPDATE gl_inv SET num_green_ml = {current_gml}"
    new_rml_qry = f"UPDATE gl_inv SET num_red_ml = {current_rml}"
    new_bml_qry = f"UPDATE gl_inv SET num_blue_ml = {current_bml}"
    new_gold_qry = f"UPDATE gl_inv SET gold = {current_gold}"
    with db.engine.begin() as connection:
        update1 = connection.execute(sqlalchemy.text(new_gml_qry))
        update2 = connection.execute(sqlalchemy.text(new_gold_qry))
        update3 = connection.execute(sqlalchemy.text(new_rml_qry))
        update4 = connection.execute(sqlalchemy.text(new_bml_qry))
    print(f"POST DELIVERED BARRELS. Barrels Delievered: {barrels_delivered} order_id: {order_id}")
    
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
    
    # Fetch the current inventory and gold
    gold_qry = "SELECT gold FROM gl_inv"
    potion_qrys = {
        "green": "SELECT num_green_potions FROM gl_inv",
        "blue": "SELECT num_blue_potions FROM gl_inv",
        "red": "SELECT num_red_potions FROM gl_inv",
        "dark": "SELECT num_dark_potions FROM gl_inv"
    }

    with db.engine.begin() as connection:
        potion_inventory = {
            "green": connection.execute(sqlalchemy.text(potion_qrys["green"])).scalar(),
            "blue": connection.execute(sqlalchemy.text(potion_qrys["blue"])).scalar(),
            "red": connection.execute(sqlalchemy.text(potion_qrys["red"])).scalar(),
            "dark": connection.execute(sqlalchemy.text(potion_qrys["dark"])).scalar()
        }
        gold = connection.execute(sqlalchemy.text(gold_qry)).scalar()

    # Calculate cost per ML for each barrel and add it to a dictionary
    
    barrel_data = []
    for barrel in wholesale_catalog:
        cost_per_ml = barrel.price / barrel.ml_per_barrel
        color = get_potion_type(barrel.potion_type)
        barrel_data.append({
            "sku": barrel.sku,
            "ml_per_barrel": barrel.ml_per_barrel,
            "potion_type": barrel.potion_type,
            "price": barrel.price,
            "quantity": barrel.quantity,
            "cost_per_ml": cost_per_ml,
            "color": color
        })

    # Sort barrels by potion type with the least inventory and then by cost per ML
    barrel_data.sort(key=lambda x: (potion_inventory[x["color"]], x["cost_per_ml"]))
    purchase_plan = []
    for barrel in barrel_data:
        if barrel["price"] <= gold and barrel["quantity"] > 0:
            barrels_to_buy = min(barrel["quantity"], gold // barrel["price"])
            total_cost = barrels_to_buy * barrel["price"]
            gold -= total_cost
            purchase_plan.append({
                "sku": barrel["sku"],
                "quantity": barrels_to_buy
            })
            barrel["quantity"] -= barrels_to_buy

    print(f"BARREL PURCHASE PLAN CALLED. SHE GAVE: {wholesale_catalog}")
    print(f"PLAN RETURNED: {purchase_plan}")
    return purchase_plan   

def get_potion_type(potion_type):
    if potion_type[0] == 1:
        return "red"
    elif potion_type[1] == 1:
        return "green"
    elif potion_type[2] == 1:
        return "blue"
    elif potion_type[3] == 1:
        return "dark"