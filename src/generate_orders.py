
import random
from datetime import datetime, timedelta


def generate_orders(
    connection,
    order_count=100,
    seed=20261022,
    scale="starter"
):

    rng = random.Random(seed)
    cursor = connection.cursor()

    products = cursor.execute("""
        SELECT sku_id, unit_price
        FROM SKU
        ORDER BY sku_id
    """).fetchall()

    zones = ["NORTH", "SOUTH", "EAST", "WEST"]

    start_date = datetime(2026, 10, 22, 8, 0)

    # Starter: 15 days | Full: 90 days
    order_days = 15 if scale == "starter" else 90

    line_count = 0

    for i in range(1, order_count + 1):

        order_id = f"ORD-2026-{i:06d}"

        order_time = start_date + timedelta(
            days=rng.randint(0, order_days - 1),
            minutes=rng.randint(0, 720)
        )

        customer_zone = rng.choice(zones)

        cursor.execute("""
            INSERT INTO "Order"
            (order_id, order_date, customer_zone, status)
            VALUES (?, ?, ?, ?)
        """, (
            order_id,
            order_time.isoformat(),
            customer_zone,
            "CREATED"
        ))

        number_of_lines = rng.randint(1, 4)

        selected_products = rng.sample(
            products,
            number_of_lines
        )

        for sku_id, unit_price in selected_products:

            line_count += 1

            cursor.execute("""
                INSERT INTO OrderLine
                (
                    order_line_id,
                    order_id,
                    sku_id,
                    quantity,
                    unit_price
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"OL-2026-{line_count:06d}",
                order_id,
                sku_id,
                rng.randint(1, 3),
                unit_price
            ))

    connection.commit()

    print("Orders generated successfully!")
    print("Total Orders:", order_count)
    print("Total Order Lines:", line_count)
