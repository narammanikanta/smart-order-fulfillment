
import csv
import os


def export_delivery_report(connection):

    cursor = connection.cursor()

    rows = cursor.execute("""
        SELECT
            o.order_id,
            p.promised_date,
            MAX(
                CASE
                    WHEN t.event_type = 'DELIVERED'
                    THEN t.event_time
                END
            ) AS actual_delivery
        FROM "Order" o
        JOIN DeliveryPromise p
            ON o.order_id = p.order_id
        LEFT JOIN Shipment s
            ON o.order_id = s.order_id
        LEFT JOIN TrackingEvent t
            ON s.shipment_id = t.shipment_id
        GROUP BY o.order_id, p.promised_date
        ORDER BY o.order_id
    """).fetchall()

    os.makedirs("reports", exist_ok=True)

    output_path = "reports/delivery_performance.csv"

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "order_id",
            "promised_date",
            "actual_delivery",
            "delivery_status"
        ])

        for order_id, promised_date, actual in rows:

            if actual is None:
                status = "MISSING"

            elif actual[:10] <= promised_date:
                status = "ON_TIME"

            else:
                status = "LATE"

            writer.writerow([
                order_id,
                promised_date,
                actual,
                status
            ])

    print("Delivery performance report exported!")
    print("File:", output_path)
    print("Total Records:", len(rows))
