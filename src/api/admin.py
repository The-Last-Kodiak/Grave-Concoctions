import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from api.inventory import update_gold, get_current_gold, update_potion_inventory, get_current_potion_inventory, update_ml, get_current_ml

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
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            TRUNCATE TABLE ledgers;
            UPDATE gl_inv SET gold = 100, num_green_ml = 0, num_red_ml = 0, num_blue_ml = 0, num_dark_ml = 0;
            UPDATE potions SET stocked = 0;
            INSERT INTO ledgers (inventory_type, change) VALUES ('gold', 100);"""))
    print("Successfully Reset Store")
    return "Successfully Reset Inventory"


