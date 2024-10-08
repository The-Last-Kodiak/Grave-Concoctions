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
    up = f"CREATE TABLE zuto_cart_{cart_id} (id bigint generated always as identity,cart_id text,customer_name text,character_class text,level int,g_pots int,r_pots int,b_pots int);"
    up1 = f"INSERT INTO zuto_cart_{cart_id} (cart_id, customer_name, character_class, level, g_pots, r_pots, b_pots) VALUES ('{cart_id}', '{new_cart.customer_name}', '{new_cart.character_class}', {new_cart.level}, 0,0,0);"
    #down = f"DROP TABLE IF EXISTS zuto_cart_mmhurwi;"
    with db.engine.begin() as connection:
        crea = connection.execute(sqlalchemy.text(up))
        crea = connection.execute(sqlalchemy.text(up1))
    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: str, item_sku: str, cart_item: CartItem):
    """Add cartitem to number of same items in the cart"""
    #WARNING: CHANGED cart_id: int TO cart_id: str
    g_ord, r_ord, b_ord = 0,0,0
    order = ""
    if item_sku == "GREEN_POTION_CONCOCTION":order = "g_pots"
    if item_sku == "BLUE_POTION_CONCOCTION":order = "b_pots"
    if item_sku == "RED_POTION_CONCOCTION":order = "r_pots"
    qry = f"UPDATE zuto_cart_{cart_id} SET {order} = {cart_item.quantity}"
    with db.engine.begin() as connection:
        update = connection.execute(sqlalchemy.text(qry))
    return {"success": True}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: str, cart_checkout: CartCheckout):
    #WARNING: CHANGED cart_id: int TO cart_id: str
    """"""
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text())
    return {"total_potions_bought": 1, "total_gold_paid": 50}

