
import random
from datetime import date, timedelta


def generate_carrier_rules(
    connection,
    seed=20261022,
    scale="starter"
):

    rng = random.Random(seed)
    cursor = connection.cursor()

    carriers = [
        row[0] for row in cursor.execute(
            "SELECT carrier_id FROM Carrier ORDER BY carrier_id"
        ).fetchall()
    ]

    services = [
        row[0] for row in cursor.execute(
            "SELECT service_id FROM ServiceLevel ORDER BY service_id"
        ).fetchall()
    ]

    zones = ["NORTH", "SOUTH", "EAST", "WEST"]

    zone_count = 0

    for carrier_id in carriers:
        for service_id in services:
            for zone in zones:

                if rng.random() < 0.20:
                    continue

                zone_count += 1

                cutoff = rng.choice([
                    "14:00",
                    "16:00",
                    "17:00",
                    "18:00"
                ])

                cursor.execute("""
                    INSERT OR IGNORE INTO CarrierServiceZone
                    (
                        zone_id,
                        carrier_id,
                        service_id,
                        destination_zone,
                        cutoff_time,
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"ZONE-2026-{zone_count:06d}",
                    carrier_id,
                    service_id,
                    zone,
                    cutoff,
                    1
                ))

    start_date = date(2026, 10, 22)

    holidays = {
        date(2026, 11, 8): "Regional Holiday",
        date(2026, 11, 14): "Holiday"
    }

    days = 60 if scale == "starter" else 150

    calendar_count = 0

    for carrier_id in carriers:
        for day in range(days):

            current_date = start_date + timedelta(days=day)

            is_weekend = current_date.weekday() == 6
            is_holiday = current_date in holidays

            working = 0 if (is_weekend or is_holiday) else 1

            calendar_count += 1

            cursor.execute("""
                INSERT OR IGNORE INTO CarrierCalendar
                (
                    calendar_id,
                    carrier_id,
                    calendar_date,
                    is_working_day,
                    holiday_name
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"CAL-2026-{calendar_count:06d}",
                carrier_id,
                current_date.isoformat(),
                working,
                holidays.get(current_date)
            ))

    connection.commit()

    print("Carrier rules generated successfully!")
    print("Carrier Calendar Records:", calendar_count)

    return zone_count, calendar_count
