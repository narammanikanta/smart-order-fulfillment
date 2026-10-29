
import sqlite3


def prepare_indexes():

    connection = sqlite3.connect(
        "fulfillment_full_working.db",
        timeout=30
    )

    try:
        cursor = connection.cursor()

        indexes = [
            """
            CREATE INDEX IF NOT EXISTS idx_orderline_order_id
            ON OrderLine(order_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_inventory_sku
            ON Inventory(sku_id, available_quantity)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_capacity_node_date
            ON WarehouseCapacity(node_id, capacity_date)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_carrier_zone
            ON CarrierServiceZone(destination_zone, active)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_calendar_carrier_date
            ON CarrierCalendar(carrier_id, calendar_date)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_shipment_order
            ON Shipment(order_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_shipmentline_orderline
            ON ShipmentLine(order_line_id)
            """
        ]

        for statement in indexes:
            cursor.execute(statement)

        connection.commit()

        print("Full-scale indexes created successfully!")
        print("Total Indexes Prepared:", len(indexes))

    finally:
        connection.close()


if __name__ == "__main__":
    prepare_indexes()
