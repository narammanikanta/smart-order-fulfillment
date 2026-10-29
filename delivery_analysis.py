
import sqlite3


def analyze_deliveries(connection):

    cursor = connection.cursor()

    results = cursor.execute("""
        SELECT
            p.order_id,
            p.promised_date,
            COUNT(s.shipment_id) AS total_shipments,
            SUM(
                CASE
                    WHEN s.shipment_status = 'DELIVERED'
                    THEN 1 ELSE 0
                END
            ) AS delivered_shipments,
            MAX(
                CASE
                    WHEN t.event_type = 'DELIVERED'
                    THEN SUBSTR(t.event_time, 1, 10)
                END
            ) AS actual_delivery_date
        FROM DeliveryPromise p
        JOIN Shipment s
            ON p.order_id = s.order_id
        LEFT JOIN (
            SELECT shipment_id, event_type, event_time
            FROM TrackingEvent
            WHERE event_type = 'DELIVERED'
        ) t ON s.shipment_id = t.shipment_id
        GROUP BY p.order_id, p.promised_date
        ORDER BY p.order_id
    """).fetchall()

    on_time = 0
    late = 0
    missing_delivery = 0

    for (
        order_id,
        promised_date,
        total_shipments,
        delivered_shipments,
        actual_date
    ) in results:

        if (
            delivered_shipments != total_shipments
            or actual_date is None
        ):
            missing_delivery += 1
            continue

        if actual_date <= promised_date:
            on_time += 1
        else:
            late += 1

    total = len(results)

    print("\nFull-Scale Delivery Performance Analysis:")
    print("Total Orders With Promises:", total)
    print("On-Time Deliveries:", on_time)
    print("Late Deliveries:", late)
    print("Incomplete Deliveries:", missing_delivery)

    if total:
        percentage = (on_time / total) * 100
        print(f"On-Time Delivery Rate: {percentage:.2f}%")
