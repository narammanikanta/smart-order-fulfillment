
# Smart Order Fulfillment & Delivery Promise System

## Project Overview
A Python and SQLite-based system for order fulfillment, inventory allocation, delivery promise calculation, shipment tracking, and anomaly detection.

## Technologies Used
- Python
- SQLite
- SQL
- CSV
- JSON

## Dataset Scale
- Orders: 50,000
- Order Lines: 124,754
- Fulfillment Nodes: 20
- Carriers: 10
- Shipments: 75,354
- Tracking Events: 100,000
- Delivery Promises: 32,409

## Core Features
1. Synthetic data generation
2. Inventory-aware order allocation
3. Warehouse capacity validation
4. Carrier scheduling
5. Delivery promise calculation
6. Shipment tracking
7. Delivery performance analysis
8. Anomaly injection and detection
9. CSV and JSON report generation

## Delivery Analysis Results
- On-Time Deliveries: 869
- Late Deliveries: 0
- Incomplete Deliveries: 31,540

Incomplete deliveries represent the current simulation state.

## Anomaly Detection Results
Five controlled anomalies were injected and successfully detected.

- True Positives: 5
- False Positives: 0
- False Negatives: 0
- Precision: 100%
- Recall: 100%

## Performance Benchmark
- Shipments Analysed: 75,354
- Tracking Events Analysed: 100,000
- Execution Time: 0.500 seconds

## Generated Reports
- reports/full_ground_truth.csv
- reports/full_detected_anomalies.csv
- reports/full_delivery_performance.csv
- reports/full_delivery_performance.json

## Important Notes
- All data is synthetic.
- Original database is preserved.
- Anomalies are injected into a separate database.
- Do not rerun generation scripts on an already populated database.
