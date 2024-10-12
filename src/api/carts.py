import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import uuid
import secrets
import string

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text())

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """Which customers visited the shop today?"""
    for custard in customers:
        up1 = f"INSERT INTO npc_visits (visit_id, customer_name, character_class, level) VALUES ({visit_id}, '{custard.customer_name}', '{custard.character_class}', {custard.level});"
        with db.engine.begin() as connection:
            puh = connection.execute(sqlalchemy.text(up1))
    #up = "CREATE TABLE npc_visits (id bigint generated always as identity,visit_id int,customer_name text,character_class text,level int);"
    custo_diction = {custo.customer_name: custo for custo in customers}
    print(customers)
    return {"success": True}


@router.post("/")
def create_cart(new_cart: Customer):
    """Creates a new cart for a specific customer."""
    cart_id = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(7))
    green_price = 50  # example price for green potions
    red_price = 50    # example price for red potions
    blue_price = 50   # example price for blue potions
    insert_command = f"""
    INSERT INTO zuto_carts (cart_id, customer_name, character_class, level, g_pots, r_pots, b_pots, g_price, r_price, b_price)
    VALUES ('{cart_id}', '{new_cart.customer_name}', '{new_cart.character_class}', {new_cart.level}, 0, 0, 0, {green_price}, {red_price}, {blue_price}); """

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(insert_command))
    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: str, item_sku: str, cart_item: CartItem):
    """Add cartitem to number of same items in the cart"""
    #WARNING: CHANGED cart_id: int TO cart_id: str
    order = {
        "GREEN_POTION_CONCOCTION": "g_pots",
        "BLUE_POTION_CONCOCTION": "b_pots",
        "RED_POTION_CONCOCTION": "r_pots"
    }.get(item_sku)

    if order:
        qry = f"UPDATE zuto_carts SET {order} = {cart_item.quantity} WHERE cart_id = '{cart_id}'"
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(qry))
        return {"success": True}
    else:
        return {"error": "Invalid item SKU"}, 400


class CartCheckout(BaseModel):
    payment: str
#changing payment: str to payment: int?

@router.post("/{cart_id}/checkout")
def checkout(cart_id: str, cart_checkout: CartCheckout):
    #WARNING: CHANGED cart_id: int TO cart_id: str
    """Processes the checkout for a specific cart."""
    with db.engine.begin() as connection:
        # Fetch the cart items and their quantities, including prices
        qry = f"""
        SELECT g_pots, r_pots, b_pots, g_price, r_price, b_price FROM zuto_carts WHERE cart_id = '{cart_id}' """
        result = connection.execute(sqlalchemy.text(qry)).fetchone()
        if not result:
            return {"error": "Cart not found"}, 404
        # Access tuple elements by position
        g_pots, r_pots, b_pots, g_price, r_price, b_price = result

        total_potions_bought = g_pots + r_pots + b_pots
        total_gold_paid = (g_pots * g_price + r_pots * r_price + b_pots * b_price)
        # Update global inventory for potions
        qry = "SELECT num_green_potions, num_red_potions, num_blue_potions, gold FROM global_inventory"
        green_potions, red_potions, blue_potions, gold = connection.execute(sqlalchemy.text(qry)).fetchone()
        print(f"Old Green Potions: {green_potions}, Old Red Potions: {red_potions}, Old Blue Potions: {blue_potions}, Old Gold: {gold}")
        new_green_potions = green_potions - g_pots
        new_red_potions = red_potions - r_pots
        new_blue_potions = blue_potions - b_pots
        new_gold = gold + total_gold_paid
        update_qry = f"""UPDATE global_inventory SET num_green_potions = {new_green_potions}, num_red_potions = {new_red_potions}, num_blue_potions = {new_blue_potions}, gold = {new_gold} """
        connection.execute(sqlalchemy.text(update_qry))
        print(f"New Green Potions: {new_green_potions}, New Red Potions: {new_red_potions}, New Blue Potions: {new_blue_potions}, NPC Paid: {total_gold_paid}, New Gold: {new_gold}")
        print(f"NPC Payment String(What could it mean?): {cart_checkout.payment}")
        
        # Clear the cart after checkout
        clear_cart_qry = f"""UPDATE zuto_carts SET g_pots = 0, r_pots = 0, b_pots = 0 WHERE cart_id = '{cart_id}' """
        new_gold_qry = f"UPDATE global_inventory SET gold = {gold}"

        return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}
