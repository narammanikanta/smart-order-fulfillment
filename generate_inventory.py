
import random

def generate_inventory(connection, seed=20261022):

    rng = random.Random(seed)
    cursor = connection.cursor()

    # Get all warehouse IDs
    cursor.execute(
        "SELECT node_id FROM FulfillmentNode ORDER BY node_id"
    )
    nodes = [row[0] for row in cursor.fetchall()]

    # Get all product IDs
    cursor.execute(
        "SELECT sku_id FROM SKU ORDER BY sku_id"
    )
    products = [row[0] for row in cursor.fetchall()]

    count = 0

    for node_id in nodes:
        for sku_id in products:

            inventory_id = f"INV-2026-{count + 1:06d}"

            # Some products intentionally unavailable
            stock = rng.randint(0, 150)

            cursor.execute("""
                INSERT OR IGNORE INTO Inventory
                (inventory_id, node_id, sku_id,
                 available_quantity, reserved_quantity)
                VALUES (?, ?, ?, ?, ?)
            """, (
                inventory_id,
                node_id,
                sku_id,
                stock,
                0
            ))

            count += 1

    connection.commit()

    print("Inventory generated successfully!")
    print("Total Inventory Records:", count)
