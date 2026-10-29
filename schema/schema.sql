
-- 1. SKU Master Table
CREATE TABLE IF NOT EXISTS SKU (
    sku_id TEXT PRIMARY KEY,
    sku_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    weight_kg REAL NOT NULL CHECK (weight_kg > 0),
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1))
);

-- 2. Fulfillment Node Table
CREATE TABLE IF NOT EXISTS FulfillmentNode (
    node_id TEXT PRIMARY KEY,
    node_name TEXT NOT NULL,
    zone TEXT NOT NULL,
    daily_capacity INTEGER NOT NULL
        CHECK (daily_capacity >= 0),
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1))
);

-- 3. Carrier Master Table
CREATE TABLE IF NOT EXISTS Carrier (
    carrier_id TEXT PRIMARY KEY,
    carrier_name TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1))
);

-- 4. Order Table
CREATE TABLE IF NOT EXISTS "Order" (
    order_id TEXT PRIMARY KEY,
    order_date TEXT NOT NULL,
    customer_zone TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'CREATED'
        CHECK (status IN (
            'CREATED',
            'ALLOCATED',
            'PARTIALLY_ALLOCATED',
            'SHIPPED',
            'DELIVERED',
            'CANCELLED'
        ))
);

-- 5. OrderLine Table
CREATE TABLE IF NOT EXISTS OrderLine (
    order_line_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),

    FOREIGN KEY (order_id) REFERENCES "Order"(order_id),
    FOREIGN KEY (sku_id) REFERENCES SKU(sku_id)
);

-- 6. Inventory Table
CREATE TABLE IF NOT EXISTS Inventory (
    inventory_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    available_quantity INTEGER NOT NULL
        CHECK (available_quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0
        CHECK (reserved_quantity >= 0),

    FOREIGN KEY (node_id)
        REFERENCES FulfillmentNode(node_id),

    FOREIGN KEY (sku_id)
        REFERENCES SKU(sku_id),

    UNIQUE(node_id, sku_id)
);

-- 7. Warehouse Capacity
CREATE TABLE IF NOT EXISTS WarehouseCapacity (
    capacity_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    capacity_date TEXT NOT NULL,
    max_orders INTEGER NOT NULL CHECK(max_orders >= 0),
    used_orders INTEGER NOT NULL DEFAULT 0
        CHECK(used_orders >= 0 AND used_orders <= max_orders),

    FOREIGN KEY(node_id)
        REFERENCES FulfillmentNode(node_id),

    UNIQUE(node_id, capacity_date)
);

-- 8. Service Level
CREATE TABLE IF NOT EXISTS ServiceLevel (
    service_id TEXT PRIMARY KEY,
    service_name TEXT NOT NULL UNIQUE,
    transit_days INTEGER NOT NULL CHECK(transit_days >= 0)
);

-- 9. Shipment
CREATE TABLE IF NOT EXISTS Shipment (
    shipment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    carrier_id TEXT NOT NULL,
    service_id TEXT NOT NULL,
    shipment_status TEXT NOT NULL DEFAULT 'CREATED',
    dispatch_date TEXT,

    FOREIGN KEY(order_id) REFERENCES "Order"(order_id),
    FOREIGN KEY(node_id) REFERENCES FulfillmentNode(node_id),
    FOREIGN KEY(carrier_id) REFERENCES Carrier(carrier_id),
    FOREIGN KEY(service_id) REFERENCES ServiceLevel(service_id)
);

-- 10. Tracking Event
CREATE TABLE IF NOT EXISTS TrackingEvent (
    tracking_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_time TEXT NOT NULL,

    FOREIGN KEY(shipment_id) REFERENCES Shipment(shipment_id)
);

-- 11. Delivery Promise
CREATE TABLE IF NOT EXISTS DeliveryPromise (
    promise_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    promised_date TEXT NOT NULL,
    created_at TEXT NOT NULL,

    FOREIGN KEY(order_id) REFERENCES "Order"(order_id)
);

-- 12. ShipmentLine
CREATE TABLE IF NOT EXISTS ShipmentLine (
    shipment_line_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    order_line_id TEXT NOT NULL,
    allocated_quantity INTEGER NOT NULL
        CHECK(allocated_quantity > 0),

    FOREIGN KEY(shipment_id)
        REFERENCES Shipment(shipment_id),

    FOREIGN KEY(order_line_id)
        REFERENCES OrderLine(order_line_id),

    UNIQUE(shipment_id, order_line_id)
);

-- 13. CarrierServiceZone
CREATE TABLE IF NOT EXISTS CarrierServiceZone (
    zone_id TEXT PRIMARY KEY,
    carrier_id TEXT NOT NULL,
    service_id TEXT NOT NULL,
    destination_zone TEXT NOT NULL,
    cutoff_time TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,

    FOREIGN KEY(carrier_id)
        REFERENCES Carrier(carrier_id),

    FOREIGN KEY(service_id)
        REFERENCES ServiceLevel(service_id),

    UNIQUE(carrier_id, service_id, destination_zone)
);

-- 14. CarrierCalendar
CREATE TABLE IF NOT EXISTS CarrierCalendar (
    calendar_id TEXT PRIMARY KEY,
    carrier_id TEXT NOT NULL,
    calendar_date TEXT NOT NULL,
    is_working_day INTEGER NOT NULL
        CHECK(is_working_day IN (0, 1)),
    holiday_name TEXT,

    FOREIGN KEY(carrier_id)
        REFERENCES Carrier(carrier_id),

    UNIQUE(carrier_id, calendar_date)
);

-- 15. InventoryEvent
CREATE TABLE IF NOT EXISTS InventoryEvent (
    inventory_event_id TEXT PRIMARY KEY,
    inventory_id TEXT NOT NULL,
    shipment_id TEXT,
    event_type TEXT NOT NULL,
    quantity_change INTEGER NOT NULL,
    event_time TEXT NOT NULL,

    FOREIGN KEY(inventory_id)
        REFERENCES Inventory(inventory_id),

    FOREIGN KEY(shipment_id)
        REFERENCES Shipment(shipment_id)
);

-- 16. OrderStatusEvent
CREATE TABLE IF NOT EXISTS OrderStatusEvent (
    status_event_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    event_time TEXT NOT NULL,

    FOREIGN KEY(order_id)
        REFERENCES "Order"(order_id)
);
