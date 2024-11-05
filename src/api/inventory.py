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
            INSERT INTO ledgers (inventory_type, change) VALUES ('gold', {change});
            UPDATE gl_inv SET gold = (SELECT SUM(change) FROM ledgers WHERE inventory_type = 'gold');"""))

def get_current_gold():
    with db.engine.begin() as connection:
        return connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(change), 0) FROM ledgers WHERE inventory_type = 'gold';")).scalar()

def update_potion_inventory(sku, change):
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"""LOCK TABLE ledgers IN EXCLUSIVE MODE;
            INSERT INTO ledgers (inventory_type, change) VALUES ('{sku}', {change});
            UPDATE potions SET stocked = (SELECT SUM(change) FROM ledgers WHERE inventory_type = '{sku}') WHERE sku = '{sku}';"""))

def get_current_potion_inventory(sku):
    with db.engine.begin() as connection:
        return connection.execute(sqlalchemy.text(f"SELECT COALESCE(SUM(change), 0) FROM ledgers WHERE inventory_type = '{sku}';")).scalar()

def update_ml(type, change):
    with db.engine.begin() as connection:
        ml_column = f"num_{type.lower()}_ml"
        connection.execute(sqlalchemy.text(f"""LOCK TABLE ledgers IN EXCLUSIVE MODE;
            INSERT INTO ledgers (inventory_type, change) VALUES ('{type}_ml', {change});
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

    """Get the full inventory of all kinds of items."""
    gl_qry = "SELECT num_green_ml, num_red_ml, num_blue_ml, num_dark_ml, gold FROM gl_inv"
    potions_qry = "SELECT sku, price, stocked FROM potions WHERE stocked > 0"
    with db.engine.begin() as connection:
        green_ml, red_ml, blue_ml, dark_ml, gold = connection.execute(sqlalchemy.text(gl_qry)).fetchone()
        potions = connection.execute(sqlalchemy.text(potions_qry)).fetchall()
    total_potions = sum([potion.stocked for potion in potions])
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
    """
    #with db.engine.begin() as connection:
        #result = connection.execute(sqlalchemy.text())

    return {
        "potion_capacity": 50,
        "ml_capacity": 10000
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
    #with db.engine.begin() as connection:
        #result = connection.execute(sqlalchemy.text())
    return "OK"
