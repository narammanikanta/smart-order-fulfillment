
from datetime import datetime
from src.delivery_promise import calculate_delivery_date


def validate_promises(connection):

    cursor = connection.cursor()

    promises = cursor.execute("""
        SELECT p.promise_id, p.order_id,
               p.promised_date, o.order_date
        FROM DeliveryPromise p
        JOIN "Order" o
            ON p.order_id = o.order_id
    """).fetchall()

    invalid_dates = 0
    incorrect_promises = 0

    for promise_id, order_id, promised_date, order_date in promises:

        # Promise cannot be before order date
        if promised_date < order_date[:10]:
            invalid_dates += 1

        shipments = cursor.execute("""
            SELECT s.carrier_id,
                   s.dispatch_date,
                   sl.transit_days
            FROM Shipment s
            JOIN ServiceLevel sl
                ON s.service_id = sl.service_id
            WHERE s.order_id = ?
        """, (order_id,)).fetchall()

        expected_dates = []

        for carrier_id, dispatch_date, transit_days in shipments:

            expected = calculate_delivery_date(
                connection,
                carrier_id,
                dispatch_date,
                transit_days
            )

            expected_dates.append(expected)

        if expected_dates and promised_date != max(expected_dates):
            incorrect_promises += 1

    print("\nDelivery Promise Validation:")
    print("Total Promises:", len(promises))
    print("Promise Before Order Errors:", invalid_dates)
    print("Incorrect Promise Calculations:", incorrect_promises)

    if invalid_dates == 0 and incorrect_promises == 0:
        print("Promise Validation: PASSED")
    else:
        print("Promise Validation: FAILED")
