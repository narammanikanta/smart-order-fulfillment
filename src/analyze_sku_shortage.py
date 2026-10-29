
import sqlite3


def analyze_sku_shortage():

    connection = sqlite3.connect(
        "fulfillment_full_working.db"
    )

    cursor = connection.cursor()

    rows = cursor.execute("""
        SELECT
            s.sku_id,
            COALESCE(d.required, 0),
            COALESCE(i.available, 0)
        FROM SKU s
        LEFT JOIN (
            SELECT sku_id, SUM(quantity) AS required
            FROM OrderLine
            GROUP BY sku_id
        ) d ON s.sku_id = d.sku_id
        LEFT JOIN (
            SELECT sku_id,
                   SUM(available_quantity) AS available
            FROM Inventory
            GROUP BY sku_id
        ) i ON s.sku_id = i.sku_id
        ORDER BY s.sku_id
    """).fetchall()

    shortage_skus = 0
    shortage_units = 0

    for sku_id, required, available in rows:

        shortage = max(0, required - available)

        if shortage > 0:
            shortage_skus += 1
            shortage_units += shortage

    print("\nSKU Shortage Analysis:")
    print("Total SKUs:", len(rows))
    print("SKUs With Shortage:", shortage_skus)
    print("SKU-Level Shortage Units:", shortage_units)

    connection.close()


if __name__ == "__main__":
    analyze_sku_shortage()
