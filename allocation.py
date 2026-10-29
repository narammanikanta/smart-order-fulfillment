
from collections import defaultdict
from datetime import datetime, timedelta
from bisect import bisect_left


def allocate_orders(connection):
    cursor = connection.cursor()

    # Load inventory once
    inventory = defaultdict(list)

    for inventory_id, node_id, sku_id, stock, zone, active in cursor.execute("""
        SELECT i.inventory_id, i.node_id, i.sku_id,
               i.available_quantity, n.zone, n.active
        FROM Inventory i
        JOIN FulfillmentNode n ON n.node_id = i.node_id
        ORDER BY i.node_id
    """):
        if active and stock > 0:
            inventory[sku_id].append({
                "id": inventory_id,
                "node": node_id,
                "stock": stock,
                "zone": zone
            })

    # Load warehouse capacity once
    capacity = {}

    for capacity_id, node_id, date, maximum, used in cursor.execute("""
        SELECT capacity_id, node_id, capacity_date,
               max_orders, used_orders
        FROM WarehouseCapacity
    """):
        capacity[(node_id, date)] = {
            "id": capacity_id,
            "remaining": maximum - used
        }

    # Load carrier services
    services = defaultdict(list)

    for carrier_id, service_id, zone, cutoff in cursor.execute("""
        SELECT carrier_id, service_id, destination_zone, cutoff_time
        FROM CarrierServiceZone
        WHERE active = 1
        ORDER BY carrier_id, service_id
    """):
        services[zone].append(
            (carrier_id, service_id, cutoff)
        )

    # Load working calendar dates
    calendars = defaultdict(list)

    for carrier_id, date in cursor.execute("""
        SELECT carrier_id, calendar_date
        FROM CarrierCalendar
        WHERE is_working_day = 1
        ORDER BY carrier_id, calendar_date
    """):
        calendars[carrier_id].append(date)

    dispatch_cache = {}

    def select_carrier(zone, order_date):
        key = (zone, order_date)

        if key in dispatch_cache:
            return dispatch_cache[key]

        order_time = datetime.fromisoformat(order_date)
        start = order_time.date()
        end = start + timedelta(days=59)

        for carrier_id, service_id, cutoff_text in services[zone]:
            cutoff = datetime.strptime(cutoff_text, "%H:%M").time()
            dates = calendars[carrier_id]

            position = bisect_left(dates, start.isoformat())

            for date_text in dates[position:]:
                check_date = datetime.fromisoformat(date_text).date()

                if check_date > end:
                    break

                if check_date == start and order_time.time() > cutoff:
                    continue

                result = (
                    carrier_id,
                    service_id,
                    datetime.combine(check_date, cutoff).isoformat()
                )

                dispatch_cache[key] = result
                return result

        dispatch_cache[key] = None
        return None

    orders = cursor.execute("""
        SELECT order_id, order_date, customer_zone
        FROM "Order"
        WHERE status = 'CREATED'
        ORDER BY order_id
    """).fetchall()

    lines_by_order = defaultdict(list)

    for line_id, order_id, sku_id, quantity in cursor.execute("""
        SELECT order_line_id, order_id, sku_id, quantity
        FROM OrderLine
        ORDER BY order_id, order_line_id
    """):
        lines_by_order[order_id].append(
            (line_id, sku_id, quantity)
        )

    shipment_count = cursor.execute(
        "SELECT COUNT(*) FROM Shipment"
    ).fetchone()[0]

    event_count = cursor.execute(
        "SELECT COUNT(*) FROM InventoryEvent"
    ).fetchone()[0]

    allocated_lines = 0
    unallocated_lines = 0

    try:
        for order_id, order_date, customer_zone in orders:
            date = order_date[:10]
            lines = lines_by_order[order_id]

            carrier = select_carrier(customer_zone, order_date)

            fully_allocated = 0
            has_shipment = False

            for line_id, sku_id, quantity in lines:
                remaining = quantity

                candidates = sorted(
                    inventory[sku_id],
                    key=lambda item: (
                        item["zone"] != customer_zone,
                        -item["stock"],
                        item["node"]
                    )
                )

                if carrier is not None:
                    carrier_id, service_id, dispatch_date = carrier

                    for item in candidates:
                        if remaining <= 0:
                            break

                        cap = capacity.get((item["node"], date))

                        if (
                            item["stock"] <= 0
                            or cap is None
                            or cap["remaining"] <= 0
                        ):
                            continue

                        qty = min(remaining, item["stock"])

                        shipment_count += 1
                        event_count += 1

                        shipment_id = f"SHP-2026-{shipment_count:06d}"

                        cursor.execute("""
                            INSERT INTO Shipment
                            (shipment_id, order_id, node_id,
                             carrier_id, service_id,
                             shipment_status, dispatch_date)
                            VALUES (?, ?, ?, ?, ?, 'ALLOCATED', ?)
                        """, (
                            shipment_id, order_id, item["node"],
                            carrier_id, service_id, dispatch_date
                        ))

                        cursor.execute("""
                            INSERT INTO ShipmentLine
                            (shipment_line_id, shipment_id,
                             order_line_id, allocated_quantity)
                            VALUES (?, ?, ?, ?)
                        """, (
                            f"SL-2026-{shipment_count:06d}",
                            shipment_id, line_id, qty
                        ))

                        cursor.execute("""
                            UPDATE Inventory
                            SET available_quantity = available_quantity - ?,
                                reserved_quantity = reserved_quantity + ?
                            WHERE inventory_id = ?
                              AND available_quantity >= ?
                        """, (qty, qty, item["id"], qty))

                        if cursor.rowcount != 1:
                            raise ValueError("Inventory reservation failed")

                        cursor.execute("""
                            UPDATE WarehouseCapacity
                            SET used_orders = used_orders + 1
                            WHERE capacity_id = ?
                              AND used_orders < max_orders
                        """, (cap["id"],))

                        if cursor.rowcount != 1:
                            raise ValueError("Warehouse capacity exceeded")

                        cursor.execute("""
                            INSERT INTO InventoryEvent
                            (inventory_event_id, inventory_id,
                             shipment_id, event_type,
                             quantity_change, event_time)
                            VALUES (?, ?, ?, 'RESERVED', ?, ?)
                        """, (
                            f"IE-2026-{event_count:06d}",
                            item["id"], shipment_id, -qty, order_date
                        ))

                        item["stock"] -= qty
                        cap["remaining"] -= 1
                        remaining -= qty
                        has_shipment = True

                if remaining == 0:
                    fully_allocated += 1
                    allocated_lines += 1
                else:
                    unallocated_lines += 1

            if fully_allocated == len(lines):
                status = "ALLOCATED"
            elif has_shipment:
                status = "PARTIALLY_ALLOCATED"
            else:
                status = "CREATED"

            if status != "CREATED":
                cursor.execute("""
                    UPDATE "Order"
                    SET status = ?
                    WHERE order_id = ?
                """, (status, order_id))

                cursor.execute("""
                    INSERT INTO OrderStatusEvent
                    (status_event_id, order_id,
                     old_status, new_status, event_time)
                    VALUES (?, ?, 'CREATED', ?, ?)
                """, (
                    f"OSE-{order_id}", order_id, status, order_date
                ))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    print("Allocation completed!")
    print("Shipments Created:", shipment_count)
    print("Fully Allocated Lines:", allocated_lines)
    print("Not Fully Allocated Lines:", unallocated_lines)
