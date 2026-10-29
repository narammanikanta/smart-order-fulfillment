
import sqlite3
import csv
import os
from datetime import datetime


EXPECTED_SEQUENCE = [
    "CREATED",
    "DISPATCHED",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED"
]


def detect_anomalies():

    connection = sqlite3.connect(
        "fulfillment_anomalies.db"
    )

    cursor = connection.cursor()
    detected = []

    shipments = cursor.execute("""
        SELECT shipment_id, order_id
        FROM Shipment
        ORDER BY shipment_id
    """).fetchall()

    for shipment_id, order_id in shipments:

        events = cursor.execute("""
            SELECT event_type, event_time
            FROM TrackingEvent
            WHERE shipment_id = ?
        """, (shipment_id,)).fetchall()

        event_types = [row[0] for row in events]

        # A001: Missing event
        if any(
            event_types.count(event) == 0
            for event in EXPECTED_SEQUENCE
        ):
            detected.append((
                "MISSING_TRACKING_EVENT",
                shipment_id,
                order_id
            ))

        # A002: Duplicate event
        if any(
            event_types.count(event) > 1
            for event in EXPECTED_SEQUENCE
        ):
            detected.append((
                "DUPLICATE_TRACKING_EVENT",
                shipment_id,
                order_id
            ))

        # A003: Incorrect chronological sequence
        if all(
            event_types.count(event) == 1
            for event in EXPECTED_SEQUENCE
        ):
            event_times = {
                event_type: datetime.fromisoformat(event_time)
                for event_type, event_time in events
            }

            ordered_times = [
                event_times[event]
                for event in EXPECTED_SEQUENCE
            ]

            if ordered_times != sorted(ordered_times):
                detected.append((
                    "INCORRECT_EVENT_SEQUENCE",
                    shipment_id,
                    order_id
                ))

    # Order-level delivery checks
    orders = cursor.execute("""
        SELECT o.order_id, o.order_date, p.promised_date
        FROM "Order" o
        JOIN DeliveryPromise p
            ON o.order_id = p.order_id
        ORDER BY o.order_id
    """).fetchall()

    for order_id, order_date, promised_date in orders:

        # A005: Promise before order date
        if promised_date < order_date[:10]:
            detected.append((
                "INCORRECT_DELIVERY_PROMISE",
                "",
                order_id
            ))
            # Do not classify this invalid promise
            # as a separate late-delivery anomaly.
            continue

        # A004: Actual delivery after promise
        result = cursor.execute("""
            SELECT MAX(t.event_time)
            FROM Shipment s
            JOIN TrackingEvent t
                ON s.shipment_id = t.shipment_id
            WHERE s.order_id = ?
              AND t.event_type = 'DELIVERED'
        """, (order_id,)).fetchone()

        if result[0] and result[0][:10] > promised_date:

            # Identify the shipment with latest delivery
            latest = cursor.execute("""
                SELECT s.shipment_id
                FROM Shipment s
                JOIN TrackingEvent t
                    ON s.shipment_id = t.shipment_id
                WHERE s.order_id = ?
                  AND t.event_type = 'DELIVERED'
                ORDER BY t.event_time DESC
                LIMIT 1
            """, (order_id,)).fetchone()

            detected.append((
                "LATE_DELIVERY",
                latest[0],
                order_id
            ))

    connection.close()

    os.makedirs("reports", exist_ok=True)

    with open(
        "reports/detected_anomalies.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "anomaly_type",
            "shipment_id",
            "order_id"
        ])

        writer.writerows(detected)

    # Compare detected anomalies against ground truth
    with open(
        "reports/ground_truth.csv",
        newline="",
        encoding="utf-8"
    ) as file:

        ground_truth = list(csv.DictReader(file))

    expected = {
        (
            row["anomaly_type"],
            row["shipment_id"],
            row["order_id"]
        )
        for row in ground_truth
    }

    actual = set(detected)

    true_positives = len(actual & expected)
    false_positives = len(actual - expected)
    false_negatives = len(expected - actual)

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives else 0
    )

    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives else 0
    )

    print("\nAnomaly Detection Results:")
    print("Ground Truth Anomalies:", len(expected))
    print("Detected Anomalies:", len(actual))
    print("True Positives:", true_positives)
    print("False Positives:", false_positives)
    print("False Negatives:", false_negatives)
    print(f"Precision: {precision:.2%}")
    print(f"Recall: {recall:.2%}")

    if actual == expected:
        print("Anomaly Detection Validation: PASSED")
    else:
        print("Anomaly Detection Validation: FAILED")

    print("Report: reports/detected_anomalies.csv")


if __name__ == "__main__":
    detect_anomalies()
