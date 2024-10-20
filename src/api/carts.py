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
        with db.engine.begin() as connection:
            dy = f"SELECT f_day FROM calendar ORDER BY r_date DESC LIMIT 1"
            day = connection.execute(sqlalchemy.text(dy)).fetchone()[0]
            up = f"INSERT INTO npc_visits (visit_id, customer_name, character_class, level, v_day) VALUES ({visit_id}, '{custard.customer_name}', '{custard.character_class}', {custard.level}, '{day}');"
            puh = connection.execute(sqlalchemy.text(up))
    #up1 = "CREATE TABLE npc_visits (id bigint generated always as identity,visit_id int,customer_name text,character_class text,level int);"
    custo_diction = {custo.customer_name: custo for custo in customers}
    print(f"CUSTOMERS VISIT: {customers}")
    return {"success": True}


@router.post("/")
def create_cart(new_cart: Customer):
    """Creates a new cart for a specific customer."""
    cart_id = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(7))
    registry = f"""
    INSERT INTO cart_owners (cart_id, name, class, lvl)
    VALUES ('{cart_id}', '{new_cart.customer_name}', '{new_cart.character_class}', {new_cart.level}); """
    #insert_command = f"""INSERT INTO zuto_carts (cart_id, g_pots, r_pots, b_pots, g_price, r_price, b_price) VALUES ('{cart_id}', 0, 0, 0, 50, 50, 50); """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(registry))
    print(f"CREATED A CART FOR CUSTOMER WITH ID: {cart_id}")
    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: str, item_sku: str, cart_item: CartItem):
    """Add cartitem to number of same items in the cart""" #WARNING: CHANGED cart_id: int TO cart_id: str
    with db.engine.begin() as connection:
        potion = connection.execute(sqlalchemy.text(f"SELECT price, stocked FROM potions WHERE sku = '{item_sku}'")).fetchone()
        if potion:
            price, stocked = potion
            if stocked >= cart_item.quantity:
                new_stock = stocked - cart_item.quantity
                turba_price = cart_item.quantity * price
                connection.execute(sqlalchemy.text(f"UPDATE potions SET stocked = {new_stock} WHERE sku = '{item_sku}'"))
                connection.execute(sqlalchemy.text(f"""
                        INSERT INTO zuto_carts (cart_id, sku, in_cart, turba_price)
                        VALUES ('{cart_id}', '{item_sku}', {cart_item.quantity}, {turba_price});"""))
                print(f"USER: {cart_id} added {item_sku} to cart this many times: {cart_item.quantity}")
                return {"success": True}
            else: return {"error": "Not enough stock available"}, 400
        else: return {"error": "Invalid item SKU"}, 400


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: str, cart_checkout: CartCheckout):
    #WARNING: CHANGED cart_id: int TO cart_id: str
    """Processes the checkout for a specific cart."""
    print(f"This customer has cart id: {cart_id}")
    print(f"NPC Payment String: {cart_checkout.payment}")
    with db.engine.begin() as connection:
        qry = f"SELECT SUM(turba_price), SUM(in_cart) FROM zuto_carts WHERE cart_id = '{cart_id}'"
        total_gold_paid, total_potions_bought = connection.execute(sqlalchemy.text(qry)).fetchone()
        if total_gold_paid is None: return {"error": "Cart not found or empty"}, 404
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM gl_inv")).scalar()
        print(f"USER: {cart_id}  Old Gold: {gold}")
        new_gold = gold + total_gold_paid
        connection.execute(sqlalchemy.text(f"UPDATE gl_inv SET gold = {new_gold}"))
        print(f"NPC Paid: {total_gold_paid}, New Gold: {new_gold}")
    return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}
