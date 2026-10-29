
import sqlite3


def analyze_capacity():

    connection = sqlite3.connect(
        "fulfillment_full_working.db"
    )

    cursor = connection.cursor()

    required_units = cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM OrderLine
    """).fetchone()[0]

    available_units = cursor.execute("""
        SELECT COALESCE(SUM(available_quantity), 0)
        FROM Inventory
    """).fetchone()[0]

    total_capacity = cursor.execute("""
        SELECT COALESCE(SUM(max_orders - used_orders), 0)
        FROM WarehouseCapacity
    """).fetchone()[0]

    total_lines = cursor.execute("""
        SELECT COUNT(*)
        FROM OrderLine
    """).fetchone()[0]

    print("\nFull-Scale Capacity Analysis:")
    print("Total Order Lines:", total_lines)
    print("Required Units:", required_units)
    print("Available Inventory Units:", available_units)
    print("Total Warehouse Capacity:", total_capacity)

    print(
        "Inventory Shortage:",
        max(0, required_units - available_units)
    )

    connection.close()


if __name__ == "__main__":
    analyze_capacity()
