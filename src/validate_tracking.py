
def validate_tracking(connection):

    cursor = connection.cursor()

    shipments = cursor.execute("""
        SELECT shipment_id, shipment_status
        FROM Shipment
        ORDER BY shipment_id
    """).fetchall()

    expected_sequence = [
        "CREATED",
        "DISPATCHED",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
        "DELIVERED"
    ]

    missing_events = 0
    sequence_errors = 0
    timestamp_errors = 0
    status_errors = 0

    for shipment_id, shipment_status in shipments:

        events = cursor.execute("""
            SELECT event_type, event_time
            FROM TrackingEvent
            WHERE shipment_id = ?
            ORDER BY event_time, tracking_id
        """, (shipment_id,)).fetchall()

        event_types = [event[0] for event in events]
        event_times = [event[1] for event in events]

        if len(events) != 5:
            missing_events += 1

        if event_types != expected_sequence:
            sequence_errors += 1

        if event_times != sorted(event_times):
            timestamp_errors += 1

        if shipment_status != "DELIVERED":
            status_errors += 1

    print("\nTracking Validation Results:")
    print("Total Shipments:", len(shipments))
    print("Incorrect Event Counts:", missing_events)
    print("Event Sequence Errors:", sequence_errors)
    print("Timestamp Order Errors:", timestamp_errors)
    print("Shipment Status Errors:", status_errors)

    if all(value == 0 for value in [
        missing_events,
        sequence_errors,
        timestamp_errors,
        status_errors
    ]):
        print("Tracking Validation: PASSED")
    else:
        print("Tracking Validation: FAILED")
