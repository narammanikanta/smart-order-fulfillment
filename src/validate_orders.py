
def validate_orders(connection):

    cursor = connection.cursor()

    # Improve lookup performance for large datasets
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_orderline_order_id
        ON OrderLine(order_id)
    """)

    connection.commit()

    # Foreign key validation
    errors = cursor.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if errors:
        print("Foreign Key Errors:", errors[:10])
        print("Total Foreign Key Errors:", len(errors))
    else:
        print("Foreign Key Validation: PASSED")

    # Orders without line items
    missing = cursor.execute("""
        SELECT COUNT(*)
        FROM "Order" o
        WHERE NOT EXISTS (
            SELECT 1
            FROM OrderLine ol
            WHERE ol.order_id = o.order_id
        )
    """).fetchone()[0]

    print("Orders without line items:", missing)

    # Duplicate Order IDs
    duplicates = cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT order_id
            FROM "Order"
            GROUP BY order_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    print("Duplicate Order IDs:", duplicates)

    if not errors and missing == 0 and duplicates == 0:
        print("Order Validation: PASSED")
    else:
        print("Order Validation: FAILED")
