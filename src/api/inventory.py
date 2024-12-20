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
        connection.execute(sqlalchemy.text(f"""
            INSERT INTO gold_ledgers (inventory_type, change, total) VALUES ('gold', {change}, COALESCE((SELECT SUM(change) FROM gold_ledgers WHERE inventory_type = 'gold'), 0) + {change});
            UPDATE gl_inv SET gold = (SELECT SUM(change) FROM gold_ledgers WHERE inventory_type = 'gold');"""))

def get_current_gold():
    with db.engine.begin() as connection:
        return connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(change), 0) FROM gold_ledgers WHERE inventory_type = 'gold';")).scalar()

def update_potion_inventory(sku, change):
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"""
            INSERT INTO potion_ledgers (inventory_type, change, total) VALUES ('{sku}', {change}, COALESCE((SELECT SUM(change) FROM potion_ledgers WHERE inventory_type = '{sku}'), 0) + {change});
            UPDATE potions SET stocked = (SELECT SUM(change) FROM potion_ledgers WHERE inventory_type = '{sku}') WHERE sku = '{sku}';"""))

def get_current_potion_inventory(sku):
    with db.engine.begin() as connection:
        return connection.execute(sqlalchemy.text(f"SELECT COALESCE(SUM(change), 0) FROM potion_ledgers WHERE inventory_type = '{sku}';")).scalar()

def update_ml(type, change):
    with db.engine.begin() as connection:
        ml_column = f"num_{type.lower()}_ml"
        connection.execute(sqlalchemy.text(f"""
            INSERT INTO ml_ledgers (inventory_type, change, total) VALUES ('{type}_ml', {change}, COALESCE((SELECT SUM(change) FROM ml_ledgers WHERE inventory_type = '{type}_ml'), 0) + {change});
            UPDATE gl_inv SET {ml_column} = (SELECT SUM(change) FROM ml_ledgers WHERE inventory_type = '{type}_ml');"""))

def get_current_ml(type):
    with db.engine.begin() as connection:
        return connection.execute(sqlalchemy.text(f"SELECT COALESCE(SUM(change), 0) FROM ml_ledgers WHERE inventory_type = '{type}_ml';")).scalar()

def update_potion_cap(change):
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"""
            INSERT INTO potion_ledgers (inventory_type, change, total) VALUES ('potion_capacity', {change}, COALESCE((SELECT SUM(change) FROM potion_ledgers WHERE inventory_type = 'potion_capacity'), 0) + {change});
            UPDATE gl_inv SET pot_cap = (SELECT SUM(change) FROM potion_ledgers WHERE inventory_type = 'potion_capacity');"""))

def update_ml_cap(change):
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"""
            INSERT INTO ml_ledgers (inventory_type, change, total) VALUES ('ml_capacity', {change}, COALESCE((SELECT SUM(change) FROM ml_ledgers WHERE inventory_type = 'ml_capacity'), 0) + {change});
            UPDATE gl_inv SET ml_cap = (SELECT SUM(change) FROM ml_ledgers WHERE inventory_type = 'ml_capacity');"""))



@router.get("/audit")
def get_inventory():
    """Get the full inventory of all kinds of items."""
    with db.engine.begin() as connection:
        query_ml = """
        SELECT inventory_type, COALESCE(SUM(change), 0) AS total FROM ml_ledgers
        WHERE inventory_type IN ('GREEN_ml', 'RED_ml', 'BLUE_ml', 'DARK_ml')
        GROUP BY inventory_type;
        """
        ml_results = connection.execute(sqlalchemy.text(query_ml)).fetchall()
        query_gold = """
        SELECT COALESCE(SUM(change), 0) AS total FROM gold_ledgers WHERE inventory_type = 'gold';
        """
        gold = connection.execute(sqlalchemy.text(query_gold)).scalar() or 0
        query_potions = """
        SELECT 
            p.sku, 
            COALESCE(SUM(pl.change), 0) AS current_inventory
        FROM 
            potions p
        LEFT JOIN 
            potion_ledgers pl ON p.sku = pl.inventory_type
        WHERE 
            p.stocked > 0
        GROUP BY 
            p.sku;
        """
        potions = connection.execute(sqlalchemy.text(query_potions)).fetchall()
    green_ml = next((item.total for item in ml_results if item.inventory_type == 'GREEN_ml'), 0)
    red_ml = next((item.total for item in ml_results if item.inventory_type == 'RED_ml'), 0)
    blue_ml = next((item.total for item in ml_results if item.inventory_type == 'BLUE_ml'), 0)
    dark_ml = next((item.total for item in ml_results if item.inventory_type == 'DARK_ml'), 0)
    potion_inventory = {potion.sku: potion.current_inventory for potion in potions}
    total_potions = sum(potion_inventory.values())
    total_ml = green_ml + red_ml + blue_ml + dark_ml
    print(f"CALLED GET INVENTORY. Green ML: {green_ml}, Red ML: {red_ml}, Blue ML: {blue_ml}, Dark ML: {dark_ml}, Number of Potions: {total_potions}, ML in Barrels: {total_ml}, Gold: {gold}")
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
    
    if capacity_purchase.potion_capacity > 0:
        update_potion_cap(50 * capacity_purchase.potion_capacity)
        
    if capacity_purchase.ml_capacity > 0:
        update_ml_cap(10000 * capacity_purchase.ml_capacity)
    
    update_gold(-total_cost)
    print(f"DELIVER CAPACITY PLAN CALLED. Order ID: {order_id}, Capacities Delivered: {capacity_purchase}")
    return "OK"
