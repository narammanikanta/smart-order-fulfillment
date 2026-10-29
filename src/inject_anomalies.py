
import sqlite3
import csv
import os
import shutil

from datetime import datetime, timedelta


def inject_anomalies():

    source = "fulfillment_clean_backup.db"
    target = "fulfillment_anomalies.db"

    # Preserve the original clean database
    shutil.copy2(source, target)

    connection = sqlite3.connect(target)
    connection.execute("PRAGMA foreign_keys = ON")

    cursor = connection.cursor()

    shipments = cursor.execute("""
        SELECT shipment_id, order_id
        FROM Shipment
        ORDER BY shipment_id
        LIMIT 4
    """).fetchall()

    if len(shipments) < 4:
        raise ValueError("At least 4 shipments required")

    ground_truth = []

    try:
        # A001: Missing tracking event
        shipment_id, order_id = shipments[0]

        cursor.execute("""
            DELETE FROM TrackingEvent
            WHERE shipment_id = ?
              AND event_type = 'IN_TRANSIT'
        """, (shipment_id,))

        ground_truth.append((
            "A001", "MISSING_TRACKING_EVENT",
            shipment_id, order_id
        ))

        # A002: Duplicate tracking event
        shipment_id, order_id = shipments[1]

        event = cursor.execute("""
            SELECT event_time
            FROM TrackingEvent
            WHERE shipment_id = ?
              AND event_type = 'IN_TRANSIT'
        """, (shipment_id,)).fetchone()

        cursor.execute("""
            INSERT INTO TrackingEvent
            (tracking_id, shipment_id, event_type, event_time)
            VALUES (?, ?, ?, ?)
        """, (
            f"ANOM-DUP-{shipment_id}",
            shipment_id,
            "IN_TRANSIT",
            event[0]
        ))

        ground_truth.append((
            "A002", "DUPLICATE_TRACKING_EVENT",
            shipment_id, order_id
        ))

        # A003: Incorrect event sequence
        shipment_id, order_id = shipments[2]

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

        ground_truth.append((
            "A003", "INCORRECT_EVENT_SEQUENCE",
            shipment_id, order_id
        ))

        # A004: Late delivery
        shipment_id, order_id = shipments[3]

        promised = cursor.execute("""
            SELECT promised_date
            FROM DeliveryPromise
            WHERE order_id = ?
        """, (order_id,)).fetchone()[0]

        late_time = (
            datetime.fromisoformat(promised)
            + timedelta(days=3, hours=12)
        ).isoformat()

        cursor.execute("""
            UPDATE TrackingEvent
            SET event_time = ?
            WHERE shipment_id = ?
              AND event_type = 'DELIVERED'
        """, (late_time, shipment_id))

        ground_truth.append((
            "A004", "LATE_DELIVERY",
            shipment_id, order_id
        ))

        # A005: Incorrect delivery promise
        target_order = cursor.execute("""
            SELECT o.order_id, o.order_date
            FROM "Order" o
            JOIN DeliveryPromise p
                ON o.order_id = p.order_id
            WHERE o.order_id NOT IN (?, ?, ?, ?)
            ORDER BY o.order_id
            LIMIT 1
        """, tuple(row[1] for row in shipments)).fetchone()

        if target_order is None:
            raise ValueError("No eligible fifth order")

        fifth_order_id, order_date = target_order

        invalid_promise = (
            datetime.fromisoformat(order_date)
            - timedelta(days=2)
        ).date().isoformat()

        cursor.execute("""
            UPDATE DeliveryPromise
            SET promised_date = ?
            WHERE order_id = ?
        """, (invalid_promise, fifth_order_id))

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

    with open(
        "reports/ground_truth.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "anomaly_id",
            "anomaly_type",
            "shipment_id",
            "order_id"
        ])

        writer.writerows(ground_truth)

    print("Anomaly injection completed!")
    print("Anomalies Injected:", len(ground_truth))
    print("Database:", target)
    print("Ground Truth: reports/ground_truth.csv")


if __name__ == "__main__":
    inject_anomalies()
