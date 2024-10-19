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


@router.get("/audit")
def get_inventory():
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
