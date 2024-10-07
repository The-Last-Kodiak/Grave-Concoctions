import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth


router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """
    Processes the delivery of potions and stores them in a dictionary.
    Args:
        potions_delivered (List[PotionInventory]): A list of delivered PotionInventory objects.
        order_id (int): The order ID for the delivery.
       """
    delivery_dictionary = {tuple(potinv.potion_type): potinv for potinv in potions_delivered}
    new_g_potions = 0
    new_r_potions = 0
    new_b_potions = 0
    for potinv in potions_delivered:
        if potinv.potion_type[1] == 1:
            new_g_potions += potinv.quantity
        if potinv.potion_type[0] == 1:
            new_r_potions += potinv.quantity
        if potinv.potion_type[2] == 1:
            new_b_potions += potinv.quantity
    g_qry = f"UPDATE global_inventory SET num_green_potions = {new_g_potions}"
    r_qry = f"UPDATE global_inventory SET num_red_potions = {new_r_potions}"
    b_qry = f"UPDATE global_inventory SET num_blue_potions = {new_b_potions}"
    with db.engine.begin() as connection:
        update1 = connection.execute(sqlalchemy.text(g_qry)) #updates amount of bottles now that they're delivered
        update2 = connection.execute(sqlalchemy.text(r_qry))
        update3 = connection.execute(sqlalchemy.text(b_qry))
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    print(f"Green Potions:{new_g_potions} Red Potions:{new_r_potions} Blue Potions:{new_b_potions}")
    
    return f"Green Potions:{new_g_potions} Red Potions:{new_r_potions} Blue Potions:{new_b_potions}"


@router.post("/plan")
def get_bottle_plan():
    """Go from barrel(ml) to bottle."""
    gml_qry = "SELECT num_green_ml FROM global_inventory"
    rml_qry = "SELECT num_red_ml FROM global_inventory"
    bml_qry = "SELECT num_blue_ml FROM global_inventory"

    with db.engine.begin() as connection:
        gml = connection.execute(sqlalchemy.text(gml_qry)).scalar()
        rml = connection.execute(sqlalchemy.text(rml_qry)).scalar()
        bml = connection.execute(sqlalchemy.text(bml_qry)).scalar()
    g_potion_order, remainder_gml = divmod(gml, 100)
    r_potion_order, remainder_rml = divmod(rml, 100)
    b_potion_order, remainder_bml = divmod(bml, 100)
    remainder_gml_qry = f"UPDATE global_inventory SET num_green_ml = {remainder_gml}"
    remainder_rml_qry = f"UPDATE global_inventory SET num_green_ml = {remainder_rml}"
    remainder_bml_qry = f"UPDATE global_inventory SET num_green_ml = {remainder_bml}"
    with db.engine.begin() as connection:
        update1 = connection.execute(sqlalchemy.text(remainder_gml_qry))
        update2 = connection.execute(sqlalchemy.text(remainder_rml_qry))
        update3 = connection.execute(sqlalchemy.text(remainder_bml_qry))
    
    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.
    # Initial logic: bottle all barrels into red potions.

    return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": g_potion_order,
            },
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": r_potion_order,
            },
            {
                "potion_type": [0, 0, 100, 0],
                "quantity": b_potion_order
            }
        ]

if __name__ == "__main__":
    print(get_bottle_plan())
