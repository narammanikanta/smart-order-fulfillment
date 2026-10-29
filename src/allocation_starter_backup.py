
from datetime import datetime, timedelta
from src.carrier_rules import calculate_dispatch_date


def allocate_orders(connection):

    cursor = connection.cursor()

    orders = cursor.execute("""
        SELECT order_id, order_date, customer_zone
        FROM "Order"
        WHERE status = 'CREATED'
        ORDER BY order_id
    """).fetchall()

    shipment_count = cursor.execute("""
        SELECT COUNT(*) FROM Shipment
    """).fetchone()[0]

    event_count = cursor.execute("""
        SELECT COUNT(*) FROM InventoryEvent
    """).fetchone()[0]

    allocated_lines = 0
    unallocated_lines = 0

    try:
        for order_id, order_date, customer_zone in orders:

            lines = cursor.execute("""
                SELECT order_line_id, sku_id, quantity
                FROM OrderLine
                WHERE order_id = ?
                ORDER BY order_line_id
            """, (order_id,)).fetchall()

            order_allocated = 0

            for order_line_id, sku_id, quantity in lines:

                remaining = quantity
                line_allocated = 0

                candidates = cursor.execute("""
                    SELECT
                        i.inventory_id,
                        i.node_id,
                        i.available_quantity,
                        wc.capacity_id
                    FROM Inventory i
                    JOIN FulfillmentNode n
                        ON i.node_id = n.node_id
                    JOIN WarehouseCapacity wc
                        ON wc.node_id = n.node_id
                    WHERE i.sku_id = ?
                      AND i.available_quantity > 0
                      AND n.active = 1
                      AND wc.capacity_date = ?
                      AND wc.used_orders < wc.max_orders
                    ORDER BY
                        CASE WHEN n.zone = ? THEN 0 ELSE 1 END,
                        i.available_quantity DESC,
                        i.node_id
                """, (
                    sku_id,
                    order_date[:10],
                    customer_zone
                )).fetchall()

                for inventory_id, node_id, stock, capacity_id in candidates:

                    if remaining <= 0:
                        break

                    carriers = cursor.execute("""
                        SELECT carrier_id, service_id
                        FROM CarrierServiceZone
                        WHERE destination_zone = ?
                          AND active = 1
                        ORDER BY carrier_id, service_id
                    """, (customer_zone,)).fetchall()

                    selected_carrier = None

                    for carrier_id, service_id in carriers:

                        dispatch_date = calculate_dispatch_date(
                            connection,
                            carrier_id,
                            service_id,
                            customer_zone,
                            order_date
                        )

                        if dispatch_date is not None:
                            selected_carrier = (
                                carrier_id,
                                service_id,
                                dispatch_date
                            )
                            break

                    if selected_carrier is None:
                        continue

                    carrier_id, service_id, dispatch_date = selected_carrier

                    allocate_qty = min(remaining, stock)

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
                        shipment_id,
                        order_id,
                        node_id,
                        carrier_id,
                        service_id,
                        dispatch_date
                    ))

                    cursor.execute("""
                        INSERT INTO ShipmentLine
                        (shipment_line_id, shipment_id,
                         order_line_id, allocated_quantity)
                        VALUES (?, ?, ?, ?)
                    """, (
                        f"SL-2026-{shipment_count:06d}",
                        shipment_id,
                        order_line_id,
                        allocate_qty
                    ))

                    cursor.execute("""
                        UPDATE Inventory
                        SET available_quantity = available_quantity - ?,
                            reserved_quantity = reserved_quantity + ?
                        WHERE inventory_id = ?
                          AND available_quantity >= ?
                    """, (
                        allocate_qty,
                        allocate_qty,
                        inventory_id,
                        allocate_qty
                    ))

                    if cursor.rowcount != 1:
                        raise ValueError("Inventory reservation failed")

                    cursor.execute("""
                        UPDATE WarehouseCapacity
                        SET used_orders = used_orders + 1
                        WHERE capacity_id = ?
                          AND used_orders < max_orders
                    """, (capacity_id,))

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
                        inventory_id,
                        shipment_id,
                        -allocate_qty,
                        order_date
                    ))

                    remaining -= allocate_qty
                    line_allocated += allocate_qty

                if line_allocated == quantity:
                    allocated_lines += 1
                    order_allocated += 1
                else:
                    unallocated_lines += 1

            if order_allocated == len(lines):
                new_status = "ALLOCATED"
            elif cursor.execute("""
                SELECT COUNT(*)
                FROM Shipment
                WHERE order_id = ?
            """, (order_id,)).fetchone()[0] > 0:
                new_status = "PARTIALLY_ALLOCATED"
            else:
                new_status = "CREATED"

            if new_status != "CREATED":

                cursor.execute("""
                    UPDATE "Order"
                    SET status = ?
                    WHERE order_id = ?
                """, (new_status, order_id))

                cursor.execute("""
                    INSERT INTO OrderStatusEvent
                    (status_event_id, order_id,
                     old_status, new_status, event_time)
                    VALUES (?, ?, 'CREATED', ?, ?)
                """, (
                    f"OSE-{order_id}",
                    order_id,
                    new_status,
                    order_date
                ))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    print("Allocation completed!")
    print("Shipments Created:", shipment_count)
    print("Fully Allocated Lines:", allocated_lines)
    print("Not Fully Allocated Lines:", unallocated_lines)
