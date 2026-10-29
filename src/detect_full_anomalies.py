
import sqlite3
import csv
import os
from collections import Counter, defaultdict


DATABASE = "fulfillment_full_anomalies.db"
GROUND_TRUTH = "reports/full_ground_truth.csv"
OUTPUT = "reports/full_detected_anomalies.csv"

EXPECTED_SEQUENCE = [
    "CREATED",
    "DISPATCHED",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED"
]

EVENT_RANK = {
    event: index
    for index, event in enumerate(EXPECTED_SEQUENCE)
}


def detect_full_anomalies():

    connection = sqlite3.connect(
        f"file:{DATABASE}?mode=ro",
        uri=True
    )
    cursor = connection.cursor()

    # Load shipments and tracking events in bulk.
    shipments = cursor.execute("""
        SELECT shipment_id, order_id, shipment_status
        FROM Shipment
        ORDER BY shipment_id
    """).fetchall()

    tracking = cursor.execute("""
        SELECT shipment_id, event_type, event_time
        FROM TrackingEvent
        ORDER BY shipment_id, event_time
    """).fetchall()

    events_by_shipment = defaultdict(list)

    for shipment_id, event_type, event_time in tracking:
        events_by_shipment[shipment_id].append(
            (event_type, event_time)
        )

    detected = set()
    delivered_by_order = defaultdict(list)

    # Shipment-level anomaly checks
    for shipment_id, order_id, status in shipments:

        events = events_by_shipment[shipment_id]
        counts = Counter(event_type for event_type, _ in events)

        # Complete sequence required only for delivered shipments.
        if status == "DELIVERED":

            if any(
                counts[event] == 0
                for event in EXPECTED_SEQUENCE
            ):
                detected.add((
                    "MISSING_TRACKING_EVENT",
                    str(shipment_id),
                    str(order_id)
                ))

        # Detect duplicate event types.
        if any(count > 1 for count in counts.values()):
            detected.add((
                "DUPLICATE_TRACKING_EVENT",
                str(shipment_id),
                str(order_id)
            ))

        # Check chronology against expected event progression.
        # Only run this check when there are no duplicate
        # or missing required events.
        if events and all(count == 1 for count in counts.values()):

            required_complete = (
                status != "DELIVERED"
                or all(counts[event] == 1 for event in EXPECTED_SEQUENCE)
            )

            if required_complete:

                chronological_ranks = [
                    EVENT_RANK[event_type]
                    for event_type, event_time in events
                    if event_type in EVENT_RANK
                ]

                if chronological_ranks != sorted(chronological_ranks):
                    detected.add((
                        "INCORRECT_EVENT_SEQUENCE",
                        str(shipment_id),
                        str(order_id)
                    ))

        # Collect actual delivered event dates for order checks.
        for event_type, event_time in events:
            if event_type == "DELIVERED":
                delivered_by_order[order_id].append(
                    (event_time[:10], shipment_id)
                )

    # Load delivery promises in one query.
    orders = cursor.execute("""
        SELECT o.order_id, o.order_date, p.promised_date
        FROM "Order" o
        JOIN DeliveryPromise p
            ON o.order_id = p.order_id
        ORDER BY o.order_id
    """).fetchall()

    for order_id, order_date, promised_date in orders:

        # Incorrect promise: promised before order placement.
        if promised_date < order_date[:10]:
            detected.add((
                "INCORRECT_DELIVERY_PROMISE",
                "",
                str(order_id)
            ))
            continue

        deliveries = delivered_by_order.get(order_id, [])

        # A delivered event occurring after the promised date.
        if deliveries:
            latest_date, latest_shipment = max(deliveries)

            if latest_date > promised_date:
                detected.add((
                    "LATE_DELIVERY",
                    str(latest_shipment),
                    str(order_id)
                ))

    connection.close()

    os.makedirs("reports", exist_ok=True)

    with open(
        OUTPUT, "w", newline="", encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "anomaly_type",
            "shipment_id",
            "order_id"
        ])

        writer.writerows(sorted(detected))

    # Compare against full-scale ground truth.
    with open(
        GROUND_TRUTH, newline="", encoding="utf-8"
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

    true_positives = len(detected & expected)
    false_positives = len(detected - expected)
    false_negatives = len(expected - detected)

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives else 0
    )

    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives else 0
    )

    print("\nFull-Scale Anomaly Detection Results:")
    print("Shipments Analysed:", len(shipments))
    print("Tracking Events Analysed:", len(tracking))
    print("Ground Truth Anomalies:", len(expected))
    print("Detected Anomalies:", len(detected))
    print("True Positives:", true_positives)
    print("False Positives:", false_positives)
    print("False Negatives:", false_negatives)
    print(f"Precision: {precision:.2%}")
    print(f"Recall: {recall:.2%}")

    if detected == expected:
        print("Anomaly Detection Validation: PASSED")
    else:
        print("Anomaly Detection Validation: NEEDS REVIEW")

        print("\nUnexpected detections:")
        for item in sorted(detected - expected)[:10]:
            print(item)

        print("\nMissed anomalies:")
        for item in sorted(expected - detected)[:10]:
            print(item)

    print("Report:", OUTPUT)


if __name__ == "__main__":
    detect_full_anomalies()
