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
    """"""
    qry = "SELECT num_green_potions, num_red_potions, num_blue_potions, num_green_ml, num_red_ml, num_blue_ml, gold FROM gl_inv"
    with db.engine.begin() as connection:
        green_potions, red_potions, blue_potions, green_ml, red_ml, blue_ml, gold = connection.execute(sqlalchemy.text(qry)).fetchone()
    total_potions = green_potions + red_potions + blue_potions
    total_ml = green_ml + red_ml + blue_ml
    print(f"CALLED GET INVENTORY. Green Potions: {green_potions}, Red Potions: {red_potions}, Blue Potions: {blue_potions}")
    print(f"Green ML: {green_ml}, Red ML: {red_ml}, Blue ML: {blue_ml}")
    print(f"Number of Potions: {total_potions}, ML in Barrels: {total_ml}, Gold: {gold}")
    
    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": gold }


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
