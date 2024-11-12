import sqlalchemy
from sqlalchemy import select
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import uuid
import secrets
import string
from src.api.inventory import update_gold, get_current_gold, update_potion_inventory, get_current_potion_inventory, update_ml, get_current_ml
from sqlalchemy import create_engine, MetaData, Table
metadata_obj = MetaData()
zuto_carts = Table("zuto_carts", metadata_obj, autoload_with=db.engine)
cart_owners = Table("cart_owners", metadata_obj, autoload_with=db.engine)
potions = Table("potions", metadata_obj, autoload_with=db.engine)


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
    query = (
        select(
            cart_owners.c.name.label("customer_name"),
            zuto_carts.c.sku.label("potion_sku"),
            zuto_carts.c.in_cart.label("total_potions_bought"),
            zuto_carts.c.turba_price.label("total_cost"),
            zuto_carts.c.r_date.label("timestamp")
        ).select_from(
            zuto_carts.join(cart_owners, zuto_carts.c.cart_id == cart_owners.c.cart_id)
                      .join(potions, zuto_carts.c.sku == potions.c.sku)
        ))
    if customer_name:
        query = query.where(cart_owners.c.name.ilike(f"%{customer_name}%"))
    if potion_sku:
        query = query.where(zuto_carts.c.sku.ilike(f"%{potion_sku}%"))

    if sort_col == search_sort_options.customer_name:
        order_by = cart_owners.c.name
    elif sort_col == search_sort_options.item_sku:
        order_by = zuto_carts.c.sku
    elif sort_col == search_sort_options.line_item_total:
        order_by = zuto_carts.c.turba_price
    else:
        order_by = zuto_carts.c.r_date

    if sort_order == search_sort_order.asc:
        query = query.order_by(order_by.asc())
    else:
        query = query.order_by(order_by.desc())

    if search_page:
        query = query.offset(int(search_page) * 5)

    with db.engine.begin() as connection:
        results_db = connection.execute(query.limit(5))
        results = []
        for row in results_db:
            results.append(
                {
                    "line_item_id": uuid.uuid1(),
                    "item_sku": f"{row.total_potions_bought} {row.potion_sku}",
                    "customer_name": row.customer_name,
                    "line_item_total": row.total_cost,
                    "timestamp": row.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            )

        prev = str(int(search_page) - 1) if search_page and int(search_page) > 0 else ""
        next_page = str(int(search_page) + 1) if len(results) >= 5 else ""

    return {
        "previous": prev,
        "next": next_page,
        "results": results,
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
            day = connection.execute(sqlalchemy.text("SELECT f_day FROM calendar ORDER BY r_date DESC LIMIT 1")).fetchone()[0]
            connection.execute(sqlalchemy.text(f"""INSERT INTO npc_visits (visit_id, customer_name, character_class, level, v_day) 
            VALUES ({visit_id}, '{custard.customer_name}', '{custard.character_class}', {custard.level}, '{day}');"""))
            day_column = day.split('day')[0]
            character_class = custard.character_class
            class_row = connection.execute(sqlalchemy.text("SELECT * FROM class_visit_days WHERE class = :class"), {"class": character_class}).fetchone()
            if not class_row:
                connection.execute(sqlalchemy.text("INSERT INTO class_visit_days (class) VALUES (:class)"), {"class": character_class})
            connection.execute(sqlalchemy.text(f'UPDATE class_visit_days SET "{day_column}" = COALESCE("{day_column}", 0) + 1 WHERE class = :class'), {"class": character_class})
    print(f"CUSTOMERS VISIT: {customers}")
    return {"success": True}


@router.post("/")
def create_cart(new_cart: Customer):
    """Creates a new cart for a specific customer."""
    cart_id = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(7))
    with db.engine.begin() as connection:
        day = connection.execute(sqlalchemy.text("SELECT f_day FROM calendar ORDER BY r_date DESC LIMIT 1")).fetchone()[0]
        registry = f"""INSERT INTO cart_owners (cart_id, name, class, lvl, day) 
        VALUES ('{cart_id}', '{new_cart.customer_name}', '{new_cart.character_class}', {new_cart.level}, '{day}'); """
        connection.execute(sqlalchemy.text(registry))
        day_column = day.split('day')[0]
        character_class = new_cart.character_class
        class_row = connection.execute(sqlalchemy.text("SELECT * FROM class_buy_days WHERE class = :class"), {"class": character_class}).fetchone()
        if not class_row:
            connection.execute(sqlalchemy.text("INSERT INTO class_buy_days (class) VALUES (:class)"), {"class": character_class})
        connection.execute(sqlalchemy.text(f'UPDATE class_buy_days SET "{day_column}" = COALESCE("{day_column}", 0) + 1 WHERE class = :class'), {"class": character_class})
    print(f"CREATED A CART FOR CUSTOMER WITH ID: {cart_id}")
    print(f"Inserted values: cart_id={cart_id}, customer_name={new_cart.customer_name}, class={new_cart.character_class}, level={new_cart.level}, day={day}")
    return {"cart_id": cart_id}



class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: str, item_sku: str, cart_item: CartItem):
    cart_id = cart_id.strip('"')  # Remove any extra quotes
    with db.engine.begin() as connection:
        potion = connection.execute(sqlalchemy.text("SELECT price, stocked FROM potions WHERE sku = :item_sku"), {"item_sku": item_sku}).fetchone()
        if potion:
            price, stocked = potion
            if stocked >= cart_item.quantity:
                turba_price = cart_item.quantity * price
                connection.execute(sqlalchemy.text("""
                    INSERT INTO zuto_carts (cart_id, sku, in_cart, turba_price)
                    VALUES (:cart_id, :item_sku, :quantity, :turba_price)
                """), {"cart_id": cart_id, "item_sku": item_sku, "quantity": cart_item.quantity, "turba_price": turba_price})
                class_text = connection.execute(sqlalchemy.text("SELECT class FROM cart_owners WHERE cart_id = :cart_id"), {"cart_id": cart_id}).scalar()
                if class_text is None:
                    return {"error": "Class not found for the given cart_id"}, 400
                class_text = class_text.strip('"')
                connection.execute(sqlalchemy.text("""INSERT INTO class_gems (class) VALUES (:class_text)ON CONFLICT (class) DO NOTHING"""), {"class_text": class_text})               
                potion_column = item_sku.split('_')[0].upper()
                connection.execute(sqlalchemy.text(f'UPDATE class_gems SET "{potion_column}" = COALESCE("{potion_column}", 0) + :quantity WHERE class = :class_text'), {"quantity": cart_item.quantity, "class_text": class_text})                
                update_potion_inventory(item_sku, -cart_item.quantity)
                print(f"USER: {cart_id} added {item_sku} to cart this many times: {cart_item.quantity}")
                return {"success": True}
            else:
                return {"error": "Not enough stock available"}, 400
        else:
            return {"error": "Invalid item SKU"}, 400


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: str, cart_checkout: CartCheckout):
    """Processes the checkout for a specific cart."""
    cart_id = cart_id.strip('"')  # Remove any extra quotes
    print(f"This customer has cart id: {cart_id}")
    print(f"NPC Payment String: {cart_checkout.payment}")
    with db.engine.begin() as connection:
        qry = "SELECT SUM(turba_price), SUM(in_cart) FROM zuto_carts WHERE cart_id = :cart_id"
        total_gold_paid, total_potions_bought = connection.execute(sqlalchemy.text(qry), {"cart_id": cart_id}).fetchone()
        if total_gold_paid is None:
            return {"error": "Cart not found or empty"}, 404
        update_gold(total_gold_paid)
        gold = get_current_gold()
        print(f"USER: {cart_id}  New Gold: {gold}")
        print(f"NPC Paid: {total_gold_paid}, New Gold: {gold}")
    return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}
