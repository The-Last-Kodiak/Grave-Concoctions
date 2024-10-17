import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    inventory = ["num_green_ml","num_green_potions","num_red_ml","num_red_potions","num_blue_ml","num_blue_potions"]
    with db.engine.begin() as connection:
        gold_qry = "UPDATE gl_inv SET gold = 100"
        update1 = connection.execute(sqlalchemy.text(gold_qry))
        for item in inventory:
            item_qry = f"UPDATE gl_inv SET {item} = 0"
            update2 = connection.execute(sqlalchemy.text(item_qry))
    print("Sucessfully Reset Store")
    return "Sucessfully Reset Inventory"

