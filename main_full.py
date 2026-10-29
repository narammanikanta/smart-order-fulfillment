
import sqlite3

from config import SEED, SCALES

from src.generate_master import generate_master_data
from src.generate_inventory import generate_inventory
from src.generate_operations import generate_operations
from src.generate_carrier_rules import generate_carrier_rules
from src.generate_orders import generate_orders
from src.validate_orders import validate_orders


DATABASE = "fulfillment_full.db"


def main():

    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        with open(
            "schema/schema.sql",
            "r",
            encoding="utf-8"
        ) as file:
            schema = file.read()

        connection.executescript(schema)

        print("Full-scale database initialized!")

        generate_master_data(connection, SEED)
        generate_inventory(connection, SEED)
        generate_operations(connection, SEED, scale="full")
        generate_carrier_rules(connection, SEED, scale="full")

        generate_orders(
            connection,
            order_count=SCALES["full"]["orders"],
            seed=SEED,
            scale="full"
        )


        validate_orders(connection)

        cursor = connection.cursor()

        total_orders = cursor.execute("""
            SELECT COUNT(*) FROM "Order"
        """).fetchone()[0]

        total_lines = cursor.execute("""
            SELECT COUNT(*) FROM OrderLine
        """).fetchone()[0]

        print("\nFull-Scale Generation Results:")
        print("Orders:", total_orders)
        print("Order Lines:", total_lines)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
