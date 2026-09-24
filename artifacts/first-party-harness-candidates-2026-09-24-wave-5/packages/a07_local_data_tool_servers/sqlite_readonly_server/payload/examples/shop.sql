CREATE TABLE customers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  country TEXT
);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers (id),
  day TEXT NOT NULL,
  amount REAL,
  status TEXT NOT NULL DEFAULT 'open'
);
CREATE VIEW paid_orders AS SELECT id, customer_id, amount FROM orders WHERE status = 'paid';
INSERT INTO customers (id, name, country) VALUES
  (1, 'Customer A', 'DE'),
  (2, 'Customer B', 'FR'),
  (3, 'Customer C', NULL);
INSERT INTO orders (id, customer_id, day, amount, status) VALUES
  (1, 1, '2025-02-01', 19.5, 'paid'),
  (2, 1, '2025-02-02', 5.0, 'paid'),
  (3, 2, '2025-02-02', NULL, 'open'),
  (4, 3, '2025-02-03', 120.0, 'refunded'),
  (5, 2, '2025-02-04', 42.25, 'paid'),
  (6, 3, '2025-02-05', 7.75, 'open');
