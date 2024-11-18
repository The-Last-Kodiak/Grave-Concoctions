import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)


def update_gold(change):
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"""LOCK TABLE ledgers IN EXCLUSIVE MODE;
            INSERT INTO ledgers (inventory_type, change, total) VALUES ('gold', {change}, COALESCE((SELECT SUM(change) FROM ledgers WHERE inventory_type = 'gold'), 0) + {change});
            UPDATE gl_inv SET gold = (SELECT SUM(change) FROM ledgers WHERE inventory_type = 'gold');"""))

def get_current_gold():
    with db.engine.begin() as connection:
        return connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(change), 0) FROM ledgers WHERE inventory_type = 'gold';")).scalar()

def update_potion_inventory(sku, change):
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"""LOCK TABLE ledgers IN EXCLUSIVE MODE;
            INSERT INTO ledgers (inventory_type, change, total) VALUES ('{sku}', {change}, COALESCE((SELECT SUM(change) FROM ledgers WHERE inventory_type = '{sku}'), 0) + {change});
            UPDATE potions SET stocked = (SELECT SUM(change) FROM ledgers WHERE inventory_type = '{sku}') WHERE sku = '{sku}';"""))

def get_current_potion_inventory(sku):
    with db.engine.begin() as connection:
        return connection.execute(sqlalchemy.text(f"SELECT COALESCE(SUM(change), 0) FROM ledgers WHERE inventory_type = '{sku}';")).scalar()

def update_ml(type, change):
    with db.engine.begin() as connection:
        ml_column = f"num_{type.lower()}_ml"
        connection.execute(sqlalchemy.text(f"""LOCK TABLE ledgers IN EXCLUSIVE MODE;
            INSERT INTO ledgers (inventory_type, change, total) VALUES ('{type}_ml', {change}, COALESCE((SELECT SUM(change) FROM ledgers WHERE inventory_type = '{type}_ml'), 0) + {change});
            UPDATE gl_inv SET {ml_column} = (SELECT SUM(change) FROM ledgers WHERE inventory_type = '{type}_ml');"""))

def get_current_ml(type):
    with db.engine.begin() as connection:
        return connection.execute(sqlalchemy.text(f"SELECT COALESCE(SUM(change), 0) FROM ledgers WHERE inventory_type = '{type}_ml';")).scalar()



@router.get("/audit")
def get_inventory():
    """Get the full inventory of all kinds of items."""
    with db.engine.begin() as connection:
        gold = get_current_gold()
        potions = connection.execute(sqlalchemy.text("SELECT sku, price FROM potions")).fetchall()
    
    potion_inventory = {potion.sku: get_current_potion_inventory(potion.sku) or 0 for potion in potions}
    total_potions = sum(potion_inventory.values())
    
    green_ml = get_current_ml("GREEN") or 0
    red_ml = get_current_ml("RED") or 0
    blue_ml = get_current_ml("BLUE") or 0
    dark_ml = get_current_ml("DARK") or 0
    total_ml = green_ml + red_ml + blue_ml + dark_ml

    print(f"CALLED GET INVENTORY. Green ML: {green_ml}, Red ML: {red_ml}, Blue ML: {blue_ml}, Dark ML: {dark_ml}")
    print(f"Number of Potions: {total_potions}, ML in Barrels: {total_ml}, Gold: {gold}")
    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": gold}


# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions 
    and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    Determines the capacity plan for potions and ml based on the available gold and current stock levels.
    Starts with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional capacity unit costs 1000 gold.
    """
    gold = get_current_gold()
    with db.engine.begin() as connection:
        pot_cap, ml_cap, p_expanse, ml_expanse = connection.execute(sqlalchemy.text("SELECT pot_cap, ml_cap, p_expanse, ml_expanse FROM gl_inv")).fetchone()
        total_potions_in_stock = connection.execute(sqlalchemy.text("SELECT SUM(stocked) FROM potions")).scalar()
        total_ml_in_stock = connection.execute(sqlalchemy.text("SELECT num_red_ml + num_green_ml + num_blue_ml + num_dark_ml FROM gl_inv")).scalar()
    print(f"Total ML: {total_ml_in_stock} with {ml_cap} ceiling")
    print(f"Total Potions: {total_potions_in_stock} with {pot_cap} ceiling")
    potion_capacity = 0
    ml_capacity = 0

    #if total_potions_in_stock >= (pot_cap - p_space) and gold >= 1000 and total_ml_in_stock >= ml_space:
    for ml in range(ml_expanse):
        if gold >= 1320:
            gold -= 1000
            ml_capacity += 1
            ml += 1
    for p in range(p_expanse):
        if gold >= 1320:
            gold -= 1000
            potion_capacity += 1
            p += 1
    #if total_potions_in_stock >= (pot_cap - p_space) and gold >= 1060:
        #gold -= 1000
        #potion_capacity += 1

    #if total_ml_in_stock >= (ml_cap - ml_space) and gold >= 1000 and total_potions_in_stock >= p_space:
    #if total_ml_in_stock >= (ml_cap - ml_space) and gold >= 1000:
        #gold -= 1000
        #ml_capacity += 1
    print(f"Buying: {potion_capacity} pot_cap & {ml_capacity} ml_cap")
    return {
        "potion_capacity": potion_capacity,
        "ml_capacity": ml_capacity
    }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions 
    and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    gold = get_current_gold()
    total_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
    if gold < total_cost:
        return {"error": "Not enough gold to purchase the requested capacities."}
    
    with db.engine.begin() as connection:
        if capacity_purchase.potion_capacity > 0 and capacity_purchase.ml_capacity > 0:
            connection.execute(sqlalchemy.text(
                "UPDATE gl_inv SET pot_cap = pot_cap + :potion_capacity, ml_cap = ml_cap + :ml_capacity"
                ), {"potion_capacity": capacity_purchase.potion_capacity * 50, "ml_capacity": capacity_purchase.ml_capacity * 10000})
            
        if capacity_purchase.potion_capacity > 0:
            connection.execute(sqlalchemy.text(
                "INSERT INTO ledgers (inventory_type, change, total) VALUES ('potion_capacity', :change, COALESCE((SELECT SUM(change) FROM ledgers WHERE inventory_type = 'potion_capacity'), 50) + :change)"
                ), {"change": 50 * capacity_purchase.potion_capacity})
        
        if capacity_purchase.ml_capacity > 0:
            connection.execute(sqlalchemy.text(
                "INSERT INTO ledgers (inventory_type, change, total) VALUES ('ml_capacity', :change, COALESCE((SELECT SUM(change) FROM ledgers WHERE inventory_type = 'ml_capacity'), 10000) + :change)"
                ), {"change": 10000 * capacity_purchase.ml_capacity})
    
    update_gold(-total_cost)
    print(f"DELIVER CAPACITY PLAN CALLED. Order ID: {order_id}, Capacities Delivered: {capacity_purchase}")
    return "OK"
