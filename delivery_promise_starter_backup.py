
from datetime import datetime, timedelta


def calculate_delivery_date(
    connection,
    carrier_id,
    dispatch_date,
    transit_days
):
    cursor = connection.cursor()

    current_date = datetime.fromisoformat(
        dispatch_date
    ).date()

    days_counted = 0

    # Count carrier working days
    while days_counted < transit_days:

        current_date += timedelta(days=1)

        result = cursor.execute("""
            SELECT is_working_day
            FROM CarrierCalendar
            WHERE carrier_id = ?
              AND calendar_date = ?
        """, (
            carrier_id,
            current_date.isoformat()
        )).fetchone()

        if result is None:
            raise ValueError(
                f"Missing carrier calendar: {current_date}"
            )

        if result[0] == 1:
            days_counted += 1

    return current_date.isoformat()


def generate_delivery_promises(connection):

    cursor = connection.cursor()

    orders = cursor.execute("""
        SELECT order_id, order_date
        FROM "Order"
        WHERE status IN (
            'ALLOCATED',
            'PARTIALLY_ALLOCATED'
        )
        ORDER BY order_id
    """).fetchall()

    promise_count = 0

    for order_id, order_date in orders:

        shipments = cursor.execute("""
            SELECT
                s.carrier_id,
                s.dispatch_date,
                sl.transit_days
            FROM Shipment s
            JOIN ServiceLevel sl
                ON s.service_id = sl.service_id
            WHERE s.order_id = ?
        """, (order_id,)).fetchall()

        if not shipments:
            continue

        delivery_dates = []

        for carrier_id, dispatch_date, transit_days in shipments:

            delivery_date = calculate_delivery_date(
                connection,
                carrier_id,
                dispatch_date,
                transit_days
            )

            delivery_dates.append(delivery_date)

        # Split orders: latest shipment delivery date
        promised_date = max(delivery_dates)

        promise_count += 1

        promise_id = f"PROM-{order_id}-01"

        cursor.execute("""
            INSERT OR IGNORE INTO DeliveryPromise
            (promise_id, order_id,
             promised_date, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            promise_id,
            order_id,
            promised_date,
            order_date
        ))

    connection.commit()

    print("Delivery promises generated successfully!")
    print("Total Promises:", promise_count)
