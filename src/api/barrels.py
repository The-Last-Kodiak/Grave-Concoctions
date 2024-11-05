import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from api.inventory import update_gold, get_current_gold, update_potion_inventory, get_current_potion_inventory, update_ml, get_current_ml

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
    for barrel in barrels_delivered:
        ml_to_add = barrel.quantity * barrel.ml_per_barrel
        total_cost = barrel.price * barrel.quantity
        
        if barrel.potion_type[1] == 1:
            update_ml("GREEN", ml_to_add)
        if barrel.potion_type[0] == 1:
            update_ml("RED", ml_to_add)
        if barrel.potion_type[2] == 1:
            update_ml("BLUE", ml_to_add)
        if barrel.potion_type[3] == 1:
            update_ml("DARK", ml_to_add)
        
        update_gold(-total_cost)

    current_gold = get_current_gold()
    current_gml = get_current_ml("GREEN")
    current_rml = get_current_ml("RED")
    current_bml = get_current_ml("BLUE")
    current_dml = get_current_ml("DARK")

    print(f"POST DELIVERED BARRELS. Barrels Delivered: {barrels_delivered} order_id: {order_id}")
    print(f"Current Gold: {current_gold}, Green ML: {current_gml}, Red ML: {current_rml}, Blue ML: {current_bml}, Dark ML: {current_dml}")

    return "OK"

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
    Generates a wholesale purchase plan that categorizes barrels by size and prioritizes buying from larger sizes first.
    Only buys one of each color before repeating the cycle, until we run out of money or barrels.
    Uses a daily spending limit if gold is more than the daily spending amount.
    If gold is above 460, buys one of each kind of mini barrel first.
    Args:
        wholesale_catalog (List[Barrel]): A list of Barrel objects representing the wholesale catalog.
    """
    daily_spending_qry = "SELECT daily_spending FROM gl_inv"
    with db.engine.begin() as connection:
        daily_spending = connection.execute(sqlalchemy.text(daily_spending_qry)).scalar()

    gold = get_current_gold()
    spending_limit = min(gold, daily_spending) if gold > daily_spending else gold

    potion_order = {
        (0, 0, 0, 1): 0,  # Dark
        (0, 0, 1, 0): 1,  # Blue
        (1, 0, 0, 0): 2,  # Red
        (0, 1, 0, 0): 3   # Green
    }

    large_barrels, medium_barrels, small_barrels, mini_barrels = [], [], [], []

    for barrel in wholesale_catalog:
        cost_per_ml = barrel.price / barrel.ml_per_barrel
        color = get_potion_type(barrel.potion_type)
        barrel_info = {
            "sku": barrel.sku,
            "ml_per_barrel": barrel.ml_per_barrel,
            "potion_type": tuple(barrel.potion_type),
            "price": barrel.price,
            "quantity": barrel.quantity,
            "cost_per_ml": cost_per_ml,
            "color": color
        }

        if barrel.ml_per_barrel >= 10000:
            large_barrels.append(barrel_info)
        elif barrel.ml_per_barrel >= 2500:
            medium_barrels.append(barrel_info)
        elif barrel.ml_per_barrel >= 500:
            small_barrels.append(barrel_info)
        else:
            mini_barrels.append(barrel_info)

    large_barrels.sort(key=lambda x: potion_order[x["potion_type"]])
    medium_barrels.sort(key=lambda x: potion_order[x["potion_type"]])
    small_barrels.sort(key=lambda x: potion_order[x["potion_type"]])
    mini_barrels.sort(key=lambda x: potion_order[x["potion_type"]])

    purchase_plan = []
    total_price = 0

    if gold > 460:
        mini_purchase = []
        for barrel in mini_barrels:
            if barrel["price"] <= spending_limit and barrel["quantity"] > 0:
                barrels_to_buy = min(1, barrel["quantity"])
                total_cost = barrels_to_buy * barrel["price"]
                if total_cost <= spending_limit:
                    spending_limit -= total_cost
                    mini_purchase.append({"sku": barrel["sku"], "quantity": barrels_to_buy})
                    barrel["quantity"] -= barrels_to_buy
                    total_price += total_cost

        mini_plan = {}
        for item in mini_purchase:
            if item['sku'] in mini_plan:
                mini_plan[item['sku']] += item['quantity']
            else:
                mini_plan[item['sku']] = item['quantity']

        purchase_plan.extend([{"sku": sku, "quantity": quantity} for sku, quantity in mini_plan.items()])

    def process_barrels(barrels, available_gold):
        purchase_list, total_spent = [], 0

        while available_gold > 0:
            updated, purchased_colors = False, set()
            for barrel in barrels:
                if barrel["price"] <= available_gold and barrel["quantity"] > 0:
                    if barrel["potion_type"] not in purchased_colors:
                        barrels_to_buy = min(1, barrel["quantity"])
                        total_cost = barrels_to_buy * barrel["price"]
                        if total_cost <= available_gold:
                            available_gold -= total_cost
                            total_spent += total_cost
                            purchase_list.append({"sku": barrel["sku"], "quantity": barrels_to_buy})
                            barrel["quantity"] -= barrels_to_buy
                            purchased_colors.add(barrel["potion_type"])
                            updated = True
                    elif len(purchased_colors) == len(potion_order):
                        barrels_to_buy = min(1, barrel["quantity"])
                        total_cost = barrels_to_buy * barrel["price"]
                        if total_cost <= available_gold:
                            available_gold -= total_cost
                            total_spent += total_cost
                            purchase_list.append({"sku": barrel["sku"], "quantity": barrels_to_buy})
                            barrel["quantity"] -= barrels_to_buy
                            updated = True
            if not updated:
                break

        return purchase_list, total_spent

    for barrels in [large_barrels, medium_barrels, small_barrels, mini_barrels]:
        category_purchase, category_spent = process_barrels(barrels, spending_limit)
        purchase_plan.extend(category_purchase)
        total_price += category_spent
        spending_limit -= category_spent

    summarized_plan = {}
    for item in purchase_plan:
        if item['sku'] in summarized_plan:
            summarized_plan[item['sku']] += item['quantity']
        else:
            summarized_plan[item['sku']] = item['quantity']

    summarized_purchase_plan = [{"sku": sku, "quantity": quantity} for sku, quantity in summarized_plan.items()]

    print(f"BARREL PURCHASE PLAN CALLED. SHE GAVE: {wholesale_catalog}")
    print(f"PLAN RETURNED: {summarized_purchase_plan}")
    print(f"TOTAL PRICE OF ALL BARRELS: {total_price}")
    return summarized_purchase_plan

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
            "color": color})
    # Sort barrels first by ml type with the least inventory, then by variety (number of different potion types) and then by cost per ML
    barrel_data.sort(key=lambda x: (ml_inventory[x["color"]], x["cost_per_ml"], -x["ml_per_barrel"], x["quantity"]))
    purchase_plan = []
    colors_purchased = set()
    min_purchase_per_color = 1
    while gold > 0:
        for barrel in barrel_data:
            if barrel["price"] <= gold and barrel["quantity"] > 0:
                # Ensure we are buying from different colors
                if len(colors_purchased) < 4 and barrel["color"] in colors_purchased:
                   continue
                barrels_to_buy = min(barrel["quantity"], gold // barrel["price"])
                total_cost = barrels_to_buy * barrel["price"]
                if colors_purchased.add(barrel["color"]) or barrels_to_buy >= min_purchase_per_color:
                    gold -= total_cost
                    purchase_plan.append({
                        "sku": barrel["sku"],
                        "quantity": barrels_to_buy
                    })
                    barrel["quantity"] -= barrels_to_buy
                    ml_inventory[barrel["color"]] += barrels_to_buy * barrel["ml_per_barrel"]
                    colors_purchased.add(barrel["color"])

                    # Resort barrels after each purchase to maintain balance in inventory
                    barrel_data.sort(key=lambda x: (ml_inventory[x["color"]], x["cost_per_ml"], -x["ml_per_barrel"], x["quantity"]))
                        
                    # Exit if gold is exhausted
                if gold <= 0:
                    break

def get_potion_type(potion_type):
    if potion_type[0] > 0:
        return "red"
    elif potion_type[1] > 0:
        return "green"
    elif potion_type[2] > 0:
        return "blue"
    elif potion_type[3] > 0:
        return "dark"