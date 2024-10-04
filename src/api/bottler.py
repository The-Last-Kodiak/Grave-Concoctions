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
    new_green_potions = 0
    for potinv in potions_delivered:
        if potinv.potion_type[1] == 1:
            new_green_potions += potinv.quantity
    qry = f"UPDATE global_inventory SET num_green_potions = {new_green_potions}"
    with db.engine.begin() as connection:
        update1 = connection.execute(sqlalchemy.text(qry)) #updates amount of bottles now that they're delivered
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    print(new_green_potions)

    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel(ml) to bottle.
    """
    green_ml_qry = "SELECT num_green_ml FROM global_inventory"
    remainder_ml = 0
    with db.engine.begin() as connection:
        green_ml = connection.execute(sqlalchemy.text(green_ml_qry)).scalar()
    green_potion_order, remainder_ml = divmod(green_ml, 100)
    remainder_ml_qry = f"UPDATE global_inventory SET num_green_ml = {remainder_ml}"
    with db.engine.begin() as connection:
        update1 = connection.execute(sqlalchemy.text(remainder_ml_qry))
    update1 = 0
    
    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.
    # Initial logic: bottle all barrels into red potions.

    return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": green_potion_order,
            }
        ]

if __name__ == "__main__":
    print(get_bottle_plan())



#post_deliver_bottles()