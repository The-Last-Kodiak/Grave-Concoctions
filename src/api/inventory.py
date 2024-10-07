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
    """ """
    gold_qry = "SELECT gold FROM global_inventory"
    g_potions_qry = "SELECT num_green_potions FROM global_inventory"
    r_potions_qry = "SELECT num_red_potions FROM global_inventory"
    b_potions_qry = "SELECT num_blue_potions FROM global_inventory"
    gml_qry = "SELECT num_green_ml FROM global_inventory"
    rml_qry = "SELECT num_red_ml FROM global_inventory"
    bml_qry = "SELECT num_blue_ml FROM global_inventory"
    with db.engine.begin() as connection:
        g_potions = connection.execute(sqlalchemy.text(g_potions_qry)).scalar()
        r_potions = connection.execute(sqlalchemy.text(r_potions_qry)).scalar()
        b_potions = connection.execute(sqlalchemy.text(b_potions_qry)).scalar()
        gold = connection.execute(sqlalchemy.text(gold_qry)).scalar()
        gml = connection.execute(sqlalchemy.text(gml_qry)).scalar()
        rml = connection.execute(sqlalchemy.text(rml_qry)).scalar()
        bml = connection.execute(sqlalchemy.text(bml_qry)).scalar()
    ml = bml + rml + gml
    potions = g_potions + r_potions + b_potions
    return {"number_of_potions": potions, "ml_in_barrels": ml, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions 
    and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text())

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
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
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text())
    return "OK"
