
import random
from datetime import datetime, timedelta


def generate_tracking(connection, seed=20261022):

    rng = random.Random(seed)
    cursor = connection.cursor()

    shipments = cursor.execute("""
        SELECT shipment_id, dispatch_date
        FROM Shipment
        WHERE shipment_status = 'ALLOCATED'
        ORDER BY shipment_id
    """).fetchall()

    event_count = 0
    delivered_count = 0

    for shipment_id, dispatch_date in shipments:

        dispatch_time = datetime.fromisoformat(dispatch_date)

        # Some shipments experience carrier delays
        delay_days = rng.choices(
            [0, 1, 2],
            weights=[80, 15, 5]
        )[0]

        events = [
            ("CREATED", dispatch_time - timedelta(hours=2)),
            ("DISPATCHED", dispatch_time),
            ("IN_TRANSIT", dispatch_time + timedelta(hours=4)),
            ("OUT_FOR_DELIVERY",
             dispatch_time + timedelta(days=2 + delay_days)),
            ("DELIVERED",
             dispatch_time + timedelta(days=2 + delay_days, hours=6))
        ]

        for sequence, (event_type, event_time) in enumerate(events, 1):

            event_count += 1

            cursor.execute("""
                INSERT INTO TrackingEvent
                (tracking_id, shipment_id, event_type, event_time)
                VALUES (?, ?, ?, ?)
            """, (
                f"TRK-{shipment_id}-{sequence:03d}",
                shipment_id,
                event_type,
                event_time.isoformat()
            ))

        cursor.execute("""
            UPDATE Shipment
            SET shipment_status = 'DELIVERED'
            WHERE shipment_id = ?
        """, (shipment_id,))

        delivered_count += 1

    connection.commit()

    print("Tracking events generated successfully!")
    print("Total Tracking Events:", event_count)
    print("Delivered Shipments:", delivered_count)
