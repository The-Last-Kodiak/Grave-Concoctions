import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from src.api.inventory import update_gold, get_current_gold, update_potion_inventory, get_current_potion_inventory, update_ml, get_current_ml

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
    with db.engine.begin() as connection: 
        daily_spending, dark_ml, red_ml, green_ml, blue_ml, ml_cap = connection.execute(sqlalchemy.text("SELECT daily_spending, num_dark_ml, num_red_ml, num_green_ml, num_blue_ml, ml_cap FROM gl_inv")).fetchone()
        typnorm = connection.execute(sqlalchemy.text("SELECT typ, norm FROM potions WHERE selling = TRUE AND norm > 0")).fetchall()
    ml_cap -= (dark_ml + red_ml + green_ml + blue_ml)
    half_average_ml = (red_ml + green_ml + blue_ml) / 6
    gold = get_current_gold()
    total_price = 0
    purchase_plan = []
    dark_barrels = []
    weighted_sum = [0, 0, 0, 0]
    for row in typnorm:
        typ, norm = row
        for z in range(len(weighted_sum)):
            weighted_sum[z] += typ[z]*norm
    print(f"Best Balance: {weighted_sum}")
    potion_order = {
        (0, 0, 0, 1): 0,  # Dark
        (0, 0, 1, 0): 1,  # Blue
        (1, 0, 0, 0): 2,  # Red
        (0, 1, 0, 0): 3   # Green
    }
    order_indices = sorted(range(len(weighted_sum)), key=lambda i: (-weighted_sum[i], i))
    best_potion_order = {}
    colors = [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)] # [Red, Green, Blue, Dark]
    for i, index in enumerate(order_indices): 
        best_potion_order[colors[index]] = i
    potion_order = best_potion_order
    
    for barrel in wholesale_catalog:
        if tuple(barrel.potion_type) == (0, 0, 0, 1):
            dark_barrels.append(barrel)
    if dark_barrels:
        dark_barrels.sort(key=lambda x: x.ml_per_barrel) 
        total_dark_ml = dark_ml
        for barrel in dark_barrels:
            if barrel.price <= gold and total_dark_ml < half_average_ml:
                barrels_to_buy = min(1, barrel.quantity)
                total_cost = barrels_to_buy * barrel.price
                if total_cost <= gold and barrel.ml_per_barrel <= ml_cap and barrels_to_buy == 1:
                    ml_cap -= barrel.ml_per_barrel
                    gold -= total_cost
                    total_price += total_cost
                    total_dark_ml += barrel.ml_per_barrel
                    purchase_plan.append({"sku": barrel.sku, "quantity": barrels_to_buy}) 
                    barrel.quantity -= barrels_to_buy
                    for b in wholesale_catalog:
                        if b.sku == barrel.sku:
                            b.quantity -= barrels_to_buy
                            break
    else:
        purchase_plan = []

    spending_limit = min(gold, daily_spending) if gold > daily_spending else gold
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
    
    if gold > 460 or blue_ml == 0 or red_ml == 0 or green_ml == 0:
        mini_purchase = []
        for barrel in mini_barrels:
            if barrel["price"] <= spending_limit and barrel["quantity"] > 0:
                barrels_to_buy = min(1, barrel["quantity"])
                total_cost = barrels_to_buy * barrel["price"]
                if total_cost <= spending_limit and barrel["ml_per_barrel"] <= ml_cap and barrels_to_buy == 1:
                    ml_cap -= barrel["ml_per_barrel"]
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

    def process_barrels(barrels, available_gold, ml_capacity):
        ml_bought = 0
        purchase_list, total_spent = [], 0
        while available_gold > 0:
            updated, purchased_colors = False, set()
            for barrel in barrels:
                if barrel["price"] <= available_gold and barrel["quantity"] > 0:
                    if barrel["potion_type"] not in purchased_colors:
                        barrels_to_buy = min(1, barrel["quantity"])
                        total_cost = barrels_to_buy * barrel["price"]
                        if total_cost <= available_gold and barrel["ml_per_barrel"] <= ml_capacity and barrels_to_buy == 1:
                            ml_capacity -= barrel["ml_per_barrel"]
                            ml_bought += barrel["ml_per_barrel"]
                            available_gold -= total_cost
                            total_spent += total_cost
                            purchase_list.append({"sku": barrel["sku"], "quantity": barrels_to_buy})
                            barrel["quantity"] -= barrels_to_buy
                            purchased_colors.add(barrel["potion_type"])
                            updated = True
                    elif len(purchased_colors) == len(potion_order):
                        barrels_to_buy = min(1, barrel["quantity"])
                        total_cost = barrels_to_buy * barrel["price"]
                        if total_cost <= available_gold and barrel["ml_per_barrel"] <= ml_capacity and barrels_to_buy == 1:
                            ml_capacity -= barrel["ml_per_barrel"]
                            ml_bought += barrel["ml_per_barrel"]
                            available_gold -= total_cost
                            total_spent += total_cost
                            purchase_list.append({"sku": barrel["sku"], "quantity": barrels_to_buy})
                            barrel["quantity"] -= barrels_to_buy
                            updated = True
            if not updated:
                break

        return purchase_list, total_spent, ml_bought


    for barrels in [large_barrels, medium_barrels, small_barrels, mini_barrels]:
        category_purchase, category_spent, ml_taken = process_barrels(barrels, spending_limit, ml_cap)
        ml_cap -= ml_taken
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


def get_potion_type(potion_type):
    if potion_type[0] > 0:
        return "red"
    elif potion_type[1] > 0:
        return "green"
    elif potion_type[2] > 0:
        return "blue"
    elif potion_type[3] > 0:
        return "dark"