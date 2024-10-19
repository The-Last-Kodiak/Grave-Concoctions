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
    gold_qry = "SELECT gold, num_green_ml, num_red_ml, num_blue_ml FROM gl_inv"
    with db.engine.begin() as connection:
        current_gold, current_gml, current_rml, current_bml = connection.execute(sqlalchemy.text(gold_qry)).fetchone()
    for barrel in barrels_delivered:
        ml_to_add = barrel.quantity * barrel.ml_per_barrel
        total_cost = barrel.price * barrel.quantity
        if barrel.potion_type[1] == 1:
            current_gml += ml_to_add
        if barrel.potion_type[0] == 1:
            current_rml += ml_to_add
        if barrel.potion_type[2] == 1:
            current_bml += ml_to_add
        current_gold -= total_cost
    update_qry = f"""UPDATE gl_inv 
        SET num_green_ml = {current_gml}, num_red_ml = {current_rml},
            num_blue_ml = {current_bml}, gold = {current_gold}"""
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(update_qry))
    print(f"POST DELIVERED BARRELS. Barrels Delivered: {barrels_delivered} order_id: {order_id}")
    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """
    Generates a wholesale purchase plan based on the current inventory of potions.
    Args:
        wholesale_catalog (List[Barrel]): A list of Barrel objects representing the wholesale catalog.
    """
    gold_qry = "SELECT gold FROM gl_inv"
    ml_qrys = {
        "green": "SELECT num_green_ml FROM gl_inv",
        "blue": "SELECT num_blue_ml FROM gl_inv",
        "red": "SELECT num_red_ml FROM gl_inv",
        "dark": "SELECT num_dark_ml FROM gl_inv"
    }

    with db.engine.begin() as connection:
        ml_inventory = {
            "green": connection.execute(sqlalchemy.text(ml_qrys["green"])).scalar(),
            "blue": connection.execute(sqlalchemy.text(ml_qrys["blue"])).scalar(),
            "red": connection.execute(sqlalchemy.text(ml_qrys["red"])).scalar(),
            "dark": connection.execute(sqlalchemy.text(ml_qrys["dark"])).scalar()
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

    # Sort barrels by ml type with the least inventory and then by cost per ML
    barrel_data.sort(key=lambda x: (ml_inventory[x["color"]], x["cost_per_ml"]))

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
    if potion_type[0] > 0:
        return "red"
    elif potion_type[1] > 0:
        return "green"
    elif potion_type[2] > 0:
        return "blue"
    elif potion_type[3] > 0:
        return "dark"