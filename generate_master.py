
import random

def generate_master_data(connection, seed=20261022):

    rng = random.Random(seed)
    cursor = connection.cursor()

    # Generate 100 Products
    categories = [
        "Electronics",
        "Clothing",
        "Home",
        "Books",
        "Sports"
    ]

    for i in range(1, 101):
        sku_id = f"SKU-2026-{i:06d}"

        cursor.execute("""
            INSERT OR IGNORE INTO SKU
            (sku_id, sku_name, category, unit_price,
             weight_kg, active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sku_id,
            f"Product {i}",
            rng.choice(categories),
            round(rng.uniform(100, 10000), 2),
            round(rng.uniform(0.1, 10), 2),
            1
        ))

    # Generate 20 Fulfillment Nodes
    zones = ["NORTH", "SOUTH", "EAST", "WEST"]

    for i in range(1, 21):
        node_id = f"FUL-2026-{i:06d}"

        cursor.execute("""
            INSERT OR IGNORE INTO FulfillmentNode
            (node_id, node_name, zone,
             daily_capacity, active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            node_id,
            f"Warehouse {i}",
            zones[(i - 1) % len(zones)],
            rng.randint(100, 500),
            1
        ))

    # Generate 10 Carriers
    for i in range(1, 11):
        carrier_id = f"CAR-2026-{i:06d}"

        cursor.execute("""
            INSERT OR IGNORE INTO Carrier
            (carrier_id, carrier_name, active)
            VALUES (?, ?, ?)
        """, (
            carrier_id,
            f"Carrier {i}",
            1
        ))

    connection.commit()

    print("Master data generated successfully!")
