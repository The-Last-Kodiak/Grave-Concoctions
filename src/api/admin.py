import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from src.api.inventory import update_gold, get_current_gold, update_potion_inventory, get_current_potion_inventory, update_ml, get_current_ml

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
            TRUNCATE TABLE potion_ledgers;
            TRUNCATE TABLE ml_ledgers;
            TRUNCATE TABLE gold_ledgers;
            UPDATE gl_inv SET gold = 100, num_green_ml = 0, num_red_ml = 0, num_blue_ml = 0, num_dark_ml = 0, pot_cap = 50, ml_cap = 10000, p_space_b4buy = 13, ml_space_b4buy = 2000;
            UPDATE potions SET stocked = 0;
            INSERT INTO gold_ledgers (inventory_type, change, total) VALUES ('gold', 100, 100);
            INSERT INTO potion_ledgers (inventory_type, change, total) VALUES ('potion_capacity', 50, 50);
            INSERT INTO ml_ledgers (inventory_type, change, total) VALUES ('ml_capacity', 10000, 10000);"""))
    print("Successfully Reset Store")
    return "Successfully Reset Inventory"


