
import sqlite3
import csv
import os
from datetime import datetime, timedelta


SOURCE = "fulfillment_full_working.db"
TARGET = "fulfillment_full_anomalies.db"
REPORT = "reports/full_ground_truth.csv"


def inject_full_anomalies():

    if os.path.exists(TARGET):
        raise FileExistsError(
            f"{TARGET} already exists. Existing data preserved."
        )

    if os.path.exists(REPORT):
        raise FileExistsError(
            f"{REPORT} already exists. Existing report preserved."
        )

    # Create a separate database using SQLite's backup API
    source = sqlite3.connect(
        f"file:{SOURCE}?mode=ro",
        uri=True
    )
    connection = sqlite3.connect(TARGET)

    try:
        source.backup(connection)
    finally:
        source.close()

    connection.execute("PRAGMA foreign_keys=ON")
    cursor = connection.cursor()

    # Select complete shipments from four different orders.
    # Prefer a single-shipment order for the late-delivery anomaly.
    candidates = cursor.execute("""
        SELECT s.shipment_id, s.order_id
        FROM Shipment s
        JOIN DeliveryPromise p ON p.order_id = s.order_id
        WHERE s.shipment_status = 'DELIVERED'
          AND (
              SELECT COUNT(DISTINCT t.event_type)
              FROM TrackingEvent t
              WHERE t.shipment_id = s.shipment_id
                AND t.event_type IN (
                    'CREATED', 'DISPATCHED', 'IN_TRANSIT',
                    'OUT_FOR_DELIVERY', 'DELIVERED'
                )
          ) = 5
        ORDER BY s.shipment_id
    """).fetchall()

    selected = []
    used_orders = set()

    for shipment_id, order_id in candidates:
        if order_id not in used_orders:
            selected.append((shipment_id, order_id))
            used_orders.add(order_id)

        if len(selected) == 3:
            break

    late_candidate = cursor.execute("""
        SELECT s.shipment_id, s.order_id
        FROM Shipment s
        JOIN DeliveryPromise p ON p.order_id = s.order_id
        WHERE s.shipment_status = 'DELIVERED'
          AND (
              SELECT COUNT(*)
              FROM Shipment x
              WHERE x.order_id = s.order_id
          ) = 1
          AND (
              SELECT COUNT(DISTINCT t.event_type)
              FROM TrackingEvent t
              WHERE t.shipment_id = s.shipment_id
                AND t.event_type IN (
                    'CREATED', 'DISPATCHED', 'IN_TRANSIT',
                    'OUT_FOR_DELIVERY', 'DELIVERED'
                )
          ) = 5
        ORDER BY s.shipment_id
    """).fetchall()

    for shipment_id, order_id in late_candidate:
        if order_id not in used_orders:
            selected.append((shipment_id, order_id))
            used_orders.add(order_id)
            break

    if len(selected) != 4:
        connection.close()
        raise ValueError(
            "Four suitable shipments from distinct orders not found."
        )

    ground_truth = []

    try:
        cursor.execute("BEGIN")

        # A001: Missing tracking event
        shipment_id, order_id = selected[0]

        cursor.execute("""
            DELETE FROM TrackingEvent
            WHERE shipment_id = ?
              AND event_type = 'IN_TRANSIT'
        """, (shipment_id,))

        if cursor.rowcount != 1:
            raise ValueError("A001 injection failed")

        ground_truth.append((
            "A001", "MISSING_TRACKING_EVENT",
            shipment_id, order_id
        ))

        # A002: Duplicate tracking event
        shipment_id, order_id = selected[1]

        event_time = cursor.execute("""
            SELECT event_time
            FROM TrackingEvent
            WHERE shipment_id = ?
              AND event_type = 'IN_TRANSIT'
        """, (shipment_id,)).fetchone()[0]

        cursor.execute("""
            INSERT INTO TrackingEvent
            (tracking_id, shipment_id, event_type, event_time)
            VALUES (?, ?, 'IN_TRANSIT', ?)
        """, (
            f"ANOM-DUP-{shipment_id}",
            shipment_id,
            event_time
        ))

        ground_truth.append((
            "A002", "DUPLICATE_TRACKING_EVENT",
            shipment_id, order_id
        ))

        # A003: Incorrect event sequence
        shipment_id, order_id = selected[2]

        dispatched = cursor.execute("""
            SELECT event_time
            FROM TrackingEvent
            WHERE shipment_id = ?
              AND event_type = 'DISPATCHED'
        """, (shipment_id,)).fetchone()[0]

        incorrect_time = (
            datetime.fromisoformat(dispatched)
            - timedelta(hours=1)
        ).isoformat()

        cursor.execute("""
            UPDATE TrackingEvent
            SET event_time = ?
            WHERE shipment_id = ?
              AND event_type = 'IN_TRANSIT'
        """, (incorrect_time, shipment_id))

        if cursor.rowcount != 1:
            raise ValueError("A003 injection failed")

        ground_truth.append((
            "A003", "INCORRECT_EVENT_SEQUENCE",
            shipment_id, order_id
        ))

        # A004: Late delivery
        shipment_id, order_id = selected[3]

        promised_date = cursor.execute("""
            SELECT promised_date
            FROM DeliveryPromise
            WHERE order_id = ?
        """, (order_id,)).fetchone()[0]

        late_time = (
            datetime.fromisoformat(promised_date)
            + timedelta(days=3, hours=15)
        ).isoformat()

        cursor.execute("""
            UPDATE TrackingEvent
            SET event_time = ?
            WHERE shipment_id = ?
              AND event_type = 'DELIVERED'
        """, (late_time, shipment_id))

        if cursor.rowcount != 1:
            raise ValueError("A004 injection failed")

        ground_truth.append((
            "A004", "LATE_DELIVERY",
            shipment_id, order_id
        ))

        # A005: Incorrect delivery promise
        fifth_order = cursor.execute("""
            SELECT o.order_id, o.order_date
            FROM "Order" o
            JOIN DeliveryPromise p ON p.order_id = o.order_id
            WHERE o.order_id NOT IN (?, ?, ?, ?)
            ORDER BY o.order_id
            LIMIT 1
        """, tuple(used_orders)).fetchone()

        if fifth_order is None:
            raise ValueError("No eligible fifth order")

        fifth_order_id, order_date = fifth_order

        invalid_promise = (
            datetime.fromisoformat(order_date)
            - timedelta(days=2)
        ).date().isoformat()

        cursor.execute("""
            UPDATE DeliveryPromise
            SET promised_date = ?
            WHERE order_id = ?
        """, (invalid_promise, fifth_order_id))

        if cursor.rowcount != 1:
            raise ValueError("A005 injection failed")

        ground_truth.append((
            "A005", "INCORRECT_DELIVERY_PROMISE",
            "", fifth_order_id
        ))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    os.makedirs("reports", exist_ok=True)

    with open(REPORT, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "anomaly_id",
            "anomaly_type",
            "shipment_id",
            "order_id"
        ])

        writer.writerows(ground_truth)

    print("Full-scale anomaly injection completed!")
    print("Anomalies Injected:", len(ground_truth))
    print("Database:", TARGET)
    print("Ground Truth:", REPORT)


if __name__ == "__main__":
    inject_full_anomalies()
