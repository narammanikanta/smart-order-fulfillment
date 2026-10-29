
from datetime import datetime, timedelta


def calculate_dispatch_date(
    connection,
    carrier_id,
    service_id,
    customer_zone,
    order_date
):
    cursor = connection.cursor()

    carrier = cursor.execute("""
        SELECT cutoff_time
        FROM CarrierServiceZone
        WHERE carrier_id = ?
          AND service_id = ?
          AND destination_zone = ?
          AND active = 1
    """, (
        carrier_id,
        service_id,
        customer_zone
    )).fetchone()

    if carrier is None:
        return None

    cutoff_time = datetime.strptime(
        carrier[0], "%H:%M"
    ).time()

    order_time = datetime.fromisoformat(order_date)
    start_date = order_time.date()
    end_date = start_date + timedelta(days=59)

    working_days = cursor.execute("""
        SELECT calendar_date
        FROM CarrierCalendar
        WHERE carrier_id = ?
          AND calendar_date BETWEEN ? AND ?
          AND is_working_day = 1
        ORDER BY calendar_date
    """, (
        carrier_id,
        start_date.isoformat(),
        end_date.isoformat()
    )).fetchall()

    for (calendar_date,) in working_days:

        check_date = datetime.fromisoformat(
            calendar_date
        ).date()

        if (
            check_date == start_date
            and order_time.time() > cutoff_time
        ):
            continue

        dispatch_time = datetime.combine(
            check_date,
            cutoff_time
        )

        return dispatch_time.isoformat()

    return None
