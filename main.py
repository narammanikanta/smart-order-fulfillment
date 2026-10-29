
import sqlite3

from config import SEED
from src.generate_master import generate_master_data
from src.generate_inventory import generate_inventory
from src.generate_operations import generate_operations
from src.generate_carrier_rules import generate_carrier_rules

from src.generate_orders import generate_orders
from config import SCALES

from src.validate_orders import validate_orders

from src.allocation import allocate_orders

from src.validate_allocation import validate_allocation





connection = sqlite3.connect("fulfillment.db")
connection.execute("PRAGMA foreign_keys = ON")

with open("schema/schema.sql", "r") as file:
    schema = file.read()



connection.executescript(schema)

print("Database schema initialized!")

generate_master_data(connection, SEED)
generate_inventory(connection, SEED)
generate_operations(connection, SEED)


generate_carrier_rules(connection, SEED)

generate_orders(
    connection,
    order_count=SCALES["starter"]["orders"],
    seed=SEED
)

allocate_orders(connection)

cursor = connection.cursor()

tables = [
    "SKU",
    "FulfillmentNode",
    "Carrier",
    "Inventory",
    "ServiceLevel",
    "WarehouseCapacity",
    "CarrierServiceZone",
    "CarrierCalendar",
    "Order",
    "OrderLine",
    "Shipment",
    "ShipmentLine",
    "InventoryEvent",
    "OrderStatusEvent"


]


for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
    print(f"{table}: {cursor.fetchone()[0]} records")


validate_orders(connection)

cursor.execute("""
    SELECT COUNT(*)
    FROM Shipment
""")

print("Existing Shipments:", cursor.fetchone()[0])

validate_allocation(connection)


connection.close()
