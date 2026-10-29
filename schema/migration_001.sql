SELECT shipment_id, shipment_status
FROM Shipment
WHERE shipment_status NOT IN (
    'CREATED',
    'ALLOCATED',
    'DISPATCHED',
    'IN_TRANSIT',
    'OUT_FOR_DELIVERY',
    'DELIVERED',
    'DELAYED',
    'CANCELLED'
);
