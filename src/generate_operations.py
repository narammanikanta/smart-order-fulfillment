
import random
from datetime import datetime, timedelta


def generate_operations(
    connection,
    seed=20261022,
    scale="starter"
):

    rng = random.Random(seed)
    cursor = connection.cursor()

    services = [
        ("SRV-001", "STANDARD", 5),
        ("SRV-002", "EXPRESS", 2),
        ("SRV-003", "SAME_DAY", 0)
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO ServiceLevel
        (service_id, service_name, transit_days)
        VALUES (?, ?, ?)
    """, services)

    nodes = cursor.execute("""
        SELECT node_id, daily_capacity
        FROM FulfillmentNode
        ORDER BY node_id
    """).fetchall()

    start_date = datetime(2026, 10, 22)

    days = 30 if scale == "starter" else 120

    count = 0

    for day in range(days):

        current_date = start_date + timedelta(days=day)

        for node_id, daily_capacity in nodes:

            count += 1

            capacity_id = f"CAP-2026-{count:06d}"

            max_orders = max(
                1,
                daily_capacity + rng.randint(-30, 30)
            )

            cursor.execute("""
                INSERT OR IGNORE INTO WarehouseCapacity
                (
                    capacity_id,
                    node_id,
                    capacity_date,
                    max_orders,
                    used_orders
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                capacity_id,
                node_id,
                current_date.strftime("%Y-%m-%d"),
                max_orders,
                0
            ))

    connection.commit()

    print("Operations data generated successfully!")
    print("Warehouse Capacity Records:", count)
