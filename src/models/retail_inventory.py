from src import database as db
from sqlalchemy.sql import text
from typing import List


class RetailInventory:
  table_name = "retail_inventory"
  def __init__(self, id, sku, name, type, quantity, recipe, price):
    self.id = id
    self.sku = sku
    self.type = type
    self.quantity = quantity
    self.recipe = recipe
    self.price = price
    self.name = name


  @staticmethod
  def get_inventory():
    # (id, sku, name, type, quantity, recipe, price)
    #get all the rows from the catalog table and return them as an array of objects
    sql_to_execute = text(f"SELECT id, sku, name, type, quantity, recipe, price FROM retail_inventory limit 1")

    inventory: List[RetailInventory]= []
    with db.engine.begin() as connection:
      result = connection.execute(sql_to_execute)
      rows = result.fetchall()
      for row in rows:
        inventory.append(RetailInventory(row[0], row[2], row[3], row[3], row[4], row[5], row[6]))
    return inventory


  def convert_to_catalog_item(self):
    return {
      "sku": self.sku,
      "name": self.name,
      "quantity": self.quantity,
      "price": self.price,
      "potion_type": self.type
    }

  



      