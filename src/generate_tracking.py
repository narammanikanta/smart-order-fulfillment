
import random
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timedelta


def generate_tracking(connection, seed=20261022):

    rng = random.Random(seed)
    cursor = connection.cursor()

    existing = cursor.execute("""
        SELECT COUNT(*) FROM TrackingEvent
    """).fetchone()[0]

    if existing:
        raise ValueError(
            "Tracking events already exist. Generation stopped."
        )

    shipments = cursor.execute("""
        SELECT s.shipment_id, s.carrier_id,
               s.dispatch_date, sl.transit_days
        FROM Shipment s
        JOIN ServiceLevel sl
          ON s.service_id = sl.service_id
        WHERE s.shipment_status = 'ALLOCATED'
        ORDER BY s.shipment_id
    """).fetchall()

    target_events = 100000
    shipment_count = len(shipments)

    if shipment_count > target_events:
        raise ValueError("Target is smaller than shipment count")

    # Every shipment receives at least one CREATED event.
    # A completed shipment requires four additional events.
    extra_events = target_events - shipment_count
    delivered_target, remainder = divmod(extra_events, 4)

    if remainder == 1:
        raise ValueError("Unsupported one-event remainder")

    calendars = defaultdict(list)

    for carrier_id, date in cursor.execute("""
        SELECT carrier_id, calendar_date
        FROM CarrierCalendar
        WHERE is_working_day = 1
        ORDER BY carrier_id, calendar_date
    """):
        calendars[carrier_id].append(date)

    def calculate_delivery_day(carrier_id, dispatch_date, transit_days):
        dispatch_day = dispatch_date[:10]

        if transit_days == 0:
            return dispatch_day

        dates = calendars[carrier_id]
        position = bisect_right(dates, dispatch_day)
        target = position + transit_days - 1

        if target >= len(dates):
            raise ValueError(
                f"Insufficient calendar for carrier {carrier_id}"
            )

        return dates[target]

    # Randomly choose which shipments have completed their journey.
    selected = list(range(shipment_count))
    rng.shuffle(selected)

    delivered_indices = set(selected[:delivered_target])
    partial_indices = set(
        selected[delivered_target:delivered_target + 1]
    ) if remainder else set()

    events_to_insert = []
    status_updates = []

    delivered_count = 0
    event_count = 0

    for index, (
        shipment_id, carrier_id, dispatch_date, transit_days
    ) in enumerate(shipments):

        dispatch_time = datetime.fromisoformat(dispatch_date)

        events = [
            ("CREATED", dispatch_time - timedelta(hours=2))
        ]

        if index in delivered_indices:

            delivery_day = calculate_delivery_day(
                carrier_id, dispatch_date, transit_days
            )

            if transit_days == 0:
                in_transit = dispatch_time + timedelta(hours=1)
                out_for_delivery = dispatch_time + timedelta(hours=2)
                delivered = dispatch_time + timedelta(hours=3)
            else:
                in_transit = dispatch_time + timedelta(hours=1)

                delivery_date = datetime.fromisoformat(delivery_day)
                out_for_delivery = delivery_date.replace(hour=9)
                delivered = delivery_date.replace(hour=15)

            events.extend([
                ("DISPATCHED", dispatch_time),
                ("IN_TRANSIT", in_transit),
                ("OUT_FOR_DELIVERY", out_for_delivery),
                ("DELIVERED", delivered)
            ])

            status_updates.append(("DELIVERED", shipment_id))
            delivered_count += 1

        elif index in partial_indices:

            events.extend([
                ("DISPATCHED", dispatch_time),
                ("IN_TRANSIT", dispatch_time + timedelta(hours=1))
            ])

            status_updates.append(("IN_TRANSIT", shipment_id))

        for sequence, (event_type, event_time) in enumerate(events, 1):

            events_to_insert.append((
                f"TRK-{shipment_id}-{sequence:03d}",
                shipment_id,
                event_type,
                event_time.isoformat()
            ))

            event_count += 1

    if event_count != target_events:
        raise ValueError(
            f"Expected {target_events}, generated {event_count}"
        )

    try:
        cursor.executemany("""
            INSERT INTO TrackingEvent
            (tracking_id, shipment_id, event_type, event_time)
            VALUES (?, ?, ?, ?)
        """, events_to_insert)

        cursor.executemany("""
            UPDATE Shipment
            SET shipment_status = ?
            WHERE shipment_id = ?
        """, status_updates)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    print("Full-scale tracking generated successfully!")
    print("Total Tracking Events:", event_count)
    print("Delivered Shipments:", delivered_count)
    print("Other Shipments:", shipment_count - delivered_count)
