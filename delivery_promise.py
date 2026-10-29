
from collections import defaultdict
from bisect import bisect_right
from datetime import datetime


def generate_delivery_promises(connection):

    cursor = connection.cursor()

    # Load working dates once
    calendars = defaultdict(list)

    for carrier_id, calendar_date in cursor.execute("""
        SELECT carrier_id, calendar_date
        FROM CarrierCalendar
        WHERE is_working_day = 1
        ORDER BY carrier_id, calendar_date
    """):
        calendars[carrier_id].append(calendar_date)

    # Load all shipment delivery information
    shipments = cursor.execute("""
        SELECT
            s.order_id,
            s.carrier_id,
            s.dispatch_date,
            sl.transit_days
        FROM Shipment s
        JOIN ServiceLevel sl
            ON s.service_id = sl.service_id
        ORDER BY s.order_id
    """).fetchall()

    latest_delivery = {}

    for order_id, carrier_id, dispatch_date, transit_days in shipments:

        dispatch_day = dispatch_date[:10]

        if transit_days == 0:
            delivery_date = dispatch_day
        else:
            dates = calendars[carrier_id]

            position = bisect_right(dates, dispatch_day)
            target = position + transit_days - 1

            if target >= len(dates):
                raise ValueError(
                    f"Insufficient carrier calendar for {carrier_id}"
                )

            delivery_date = dates[target]

        if (
            order_id not in latest_delivery
            or delivery_date > latest_delivery[order_id]
        ):
            latest_delivery[order_id] = delivery_date

    orders = cursor.execute("""
        SELECT order_id, order_date
        FROM "Order"
        WHERE status IN ('ALLOCATED', 'PARTIALLY_ALLOCATED')
        ORDER BY order_id
    """).fetchall()

    promise_count = 0

    try:
        for order_id, order_date in orders:

            promised_date = latest_delivery.get(order_id)

            if promised_date is None:
                continue

            promise_id = f"PROM-{order_id}-01"

            cursor.execute("""
                INSERT OR IGNORE INTO DeliveryPromise
                (promise_id, order_id, promised_date, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                promise_id,
                order_id,
                promised_date,
                order_date
            ))

            promise_count += cursor.rowcount

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    print("Delivery promises generated successfully!")
    print("Total Promises:", promise_count)
