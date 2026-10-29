
import sqlite3
import csv
import json
import os

DATABASE = "fulfillment_full_working.db"
REPORT_DIR = "reports"


def export_full_reports():

    os.makedirs(REPORT_DIR, exist_ok=True)

    connection = sqlite3.connect(
        f"file:{DATABASE}?mode=ro",
        uri=True
    )
    cursor = connection.cursor()

    query = """
        SELECT
            p.order_id,
            p.promised_date,
            COUNT(s.shipment_id) AS total_shipments,
            SUM(
                CASE WHEN s.shipment_status = 'DELIVERED'
                THEN 1 ELSE 0 END
            ) AS delivered_shipments,
            MAX(
                CASE WHEN t.event_type = 'DELIVERED'
                THEN SUBSTR(t.event_time, 1, 10)
                END
            ) AS actual_delivery_date
        FROM DeliveryPromise p
        JOIN Shipment s ON p.order_id = s.order_id
        LEFT JOIN TrackingEvent t
            ON s.shipment_id = t.shipment_id
            AND t.event_type = 'DELIVERED'
        GROUP BY p.order_id, p.promised_date
        ORDER BY p.order_id
    """

    rows = cursor.execute(query).fetchall()
    connection.close()

    columns = [
        "order_id",
        "promised_date",
        "total_shipments",
        "delivered_shipments",
        "actual_delivery_date",
        "delivery_status"
    ]

    records = []

    for order_id, promised, total, delivered, actual in rows:

        if delivered != total or actual is None:
            status = "INCOMPLETE"
        elif actual <= promised:
            status = "ON_TIME"
        else:
            status = "LATE"

        records.append({
            "order_id": order_id,
            "promised_date": promised,
            "total_shipments": total,
            "delivered_shipments": delivered,
            "actual_delivery_date": actual,
            "delivery_status": status
        })

    csv_path = os.path.join(
        REPORT_DIR, "full_delivery_performance.csv"
    )

    json_path = os.path.join(
        REPORT_DIR, "full_delivery_performance.json"
    )

    for path in (csv_path, json_path):
        if os.path.exists(path):
            raise FileExistsError(
                f"Report already exists: {path}"
            )

    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)

    print("\nFull-Scale Reports Exported Successfully!")
    print("Total Records:", len(records))
    print("CSV:", csv_path)
    print("JSON:", json_path)


if __name__ == "__main__":
    export_full_reports()
