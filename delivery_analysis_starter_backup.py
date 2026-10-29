
from datetime import datetime


def analyze_deliveries(connection):

    cursor = connection.cursor()

    orders = cursor.execute("""
        SELECT o.order_id, p.promised_date
        FROM "Order" o
        JOIN DeliveryPromise p
            ON o.order_id = p.order_id
        ORDER BY o.order_id
    """).fetchall()

    on_time = 0
    late = 0
    missing_delivery = 0

    for order_id, promised_date in orders:

        result = cursor.execute("""
            SELECT MAX(t.event_time)
            FROM Shipment s
            JOIN TrackingEvent t
                ON s.shipment_id = t.shipment_id
            WHERE s.order_id = ?
              AND t.event_type = 'DELIVERED'
        """, (order_id,)).fetchone()

        if result[0] is None:
            missing_delivery += 1
            continue

        actual_date = datetime.fromisoformat(
            result[0]
        ).date()

        promised = datetime.fromisoformat(
            promised_date
        ).date()

        if actual_date <= promised:
            on_time += 1
        else:
            late += 1

    print("\nDelivery Performance Analysis:")
    print("Total Orders:", len(orders))
    print("On-Time Deliveries:", on_time)
    print("Late Deliveries:", late)
    print("Missing Deliveries:", missing_delivery)

    if orders:
        percentage = (on_time / len(orders)) * 100
        print(f"On-Time Delivery Rate: {percentage:.2f}%")
