
def validate_allocation(connection):

    cursor = connection.cursor()

    # Check negative inventory
    negative_stock = cursor.execute("""
        SELECT COUNT(*)
        FROM Inventory
        WHERE available_quantity < 0
           OR reserved_quantity < 0
    """).fetchone()[0]

    # Check warehouse capacity violations
    capacity_errors = cursor.execute("""
        SELECT COUNT(*)
        FROM WarehouseCapacity
        WHERE used_orders > max_orders
    """).fetchone()[0]

    # Check over-allocation
    allocation_errors = cursor.execute("""
        SELECT COUNT(*)
        FROM OrderLine ol
        WHERE (
            SELECT COALESCE(SUM(sl.allocated_quantity), 0)
            FROM ShipmentLine sl
            WHERE sl.order_line_id = ol.order_line_id
        ) > ol.quantity
    """).fetchone()[0]

    # Check inventory reservation events
    event_errors = cursor.execute("""
        SELECT COUNT(*)
        FROM Inventory i
        WHERE i.reserved_quantity != COALESCE((
            SELECT -SUM(e.quantity_change)
            FROM InventoryEvent e
            WHERE e.inventory_id = i.inventory_id
              AND e.event_type = 'RESERVED'
        ), 0)
    """).fetchone()[0]

    print("\nAllocation Validation Results:")
    print("Negative Inventory:", negative_stock)
    print("Capacity Violations:", capacity_errors)
    print("Over-Allocation Errors:", allocation_errors)
    print("Inventory Event Mismatches:", event_errors)

    if all(value == 0 for value in [
        negative_stock,
        capacity_errors,
        allocation_errors,
        event_errors
    ]):
        print("Allocation Validation: PASSED")
    else:
        print("Allocation Validation: FAILED")
