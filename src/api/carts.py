import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum


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
        result = connection.execute(sqlalchemy.text(f"""
            SELECT line_item_id, item_sku, customer_name, line_item_total, timestamp
            FROM orders
            WHERE customer_name ILIKE :customer_name
            AND item_sku ILIKE :potion_sku
            ORDER BY {sort_col} {sort_order}
            LIMIT 5 OFFSET :search_page
        """), {
            "customer_name": f"%{customer_name}%",
            "potion_sku": f"%{potion_sku}%",
            "search_page": int(search_page) * 5
        })
        orders = result.fetchall()
        previous_page = int(search_page) - 1 if int(search_page) > 0 else None
        next_page = int(search_page) + 1 if len(orders) == 5 else None
    return {
        "previous": previous_page,
        "next": next_page,
        "results": [
            {
                "line_item_id": row['line_item_id'],
                "item_sku": row['item_sku'],
                "customer_name": row['customer_name'],
                "line_item_total": row['line_item_total'],
                "timestamp": row['timestamp'],
            }
            for row in orders
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Shares the customers that visited the store on that tick.
    Not all customers end up purchasing because they may not like what they see in the current catalog.
    """
    success = True
    try:
        with db.engine.begin() as connection:
            for customer in customers:
                # Check if the customer visit already exists
                result = connection.execute(sqlalchemy.text("""
                    SELECT 1
                    FROM visits
                    WHERE visit_id = :visit_id AND customer_name = :customer_name
                """), {
                    "visit_id": visit_id,
                    "customer_name": customer.customer_name
                })
                existing_visit = result.fetchone()

                if existing_visit:
                    # Update the visit if it exists
                    connection.execute(sqlalchemy.text("""
                        UPDATE visits
                        SET character_class = :character_class, level = :level
                        WHERE visit_id = :visit_id AND customer_name = :customer_name
                    """), {
                        "visit_id": visit_id,
                        "customer_name": customer.customer_name,
                        "character_class": customer.character_class,
                        "level": customer.level
                    })
                else:
                    # Insert the visit if it does not exist
                    connection.execute(sqlalchemy.text("""
                        INSERT INTO visits (visit_id, customer_name, character_class, level)
                        VALUES (:visit_id, :customer_name, :character_class, :level)
                    """), {
                        "visit_id": visit_id,
                        "customer_name": customer.customer_name,
                        "character_class": customer.character_class,
                        "level": customer.level
                    })
    except Exception as e:
        print(f"Error recording visits: {e}")
        success = False

    return {"success": success}


@router.post("/")
def create_cart(new_cart: Customer):
    """
    Creates a new cart for a specific customer.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO carts (customer_name, character_class, level)
            VALUES (:customer_name, :character_class, :level)
            RETURNING cart_id
        """), {
            "customer_name": new_cart.customer_name,
            "character_class": new_cart.character_class,
            "level": new_cart.level
        })
        cart_id = result.fetchone()['cart_id']
    return {"cart_id": str(cart_id)}
    #return {"cart_id": 1}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """
    Updates the quantity of a specific item in a cart.
    """
    success = True
    try:
        with db.engine.begin() as connection:
            # Check if the item already exists in the cart
            result = connection.execute(sqlalchemy.text("""
                SELECT quantity
                FROM cart_items
                WHERE cart_id = :cart_id AND item_sku = :item_sku
            """), {
                "cart_id": cart_id,
                "item_sku": item_sku
            })
            existing_item = result.fetchone()

            if existing_item:
                # Update the quantity if the item exists
                connection.execute(sqlalchemy.text("""
                    UPDATE cart_items
                    SET quantity = :quantity
                    WHERE cart_id = :cart_id AND item_sku = :item_sku
                """), {
                    "quantity": cart_item.quantity,
                    "cart_id": cart_id,
                    "item_sku": item_sku
                })
            else:
                # Insert the item if it does not exist
                connection.execute(sqlalchemy.text("""
                    INSERT INTO cart_items (cart_id, item_sku, quantity)
                    VALUES (:cart_id, :item_sku, :quantity)
                """), {
                    "cart_id": cart_id,
                    "item_sku": item_sku,
                    "quantity": cart_item.quantity
                })
    except Exception as e:
        print(f"Error updating item quantity: {e}")
        success = False

    return {"success": success}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT SUM(ci.quantity * p.price) AS total_gold_paid, SUM(ci.quantity) AS total_potions_bought
            FROM cart_items ci
            JOIN potions p ON ci.item_sku = p.sku
            WHERE ci.cart_id = :cart_id
        """), {"cart_id": cart_id})
        totals = result.fetchone()

        # Clear the cart after checkout
        connection.execute(sqlalchemy.text("""
            DELETE FROM cart_items WHERE cart_id = :cart_id
        """), {"cart_id": cart_id})
        
    return {
        "total_potions_bought": totals['total_potions_bought'],
        "total_gold_paid": totals['total_gold_paid']
    }
        #return {"total_potions_bought": 1, "total_gold_paid": 50}

