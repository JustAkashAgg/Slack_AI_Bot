-- Seed data for public.sales_daily
-- Safe to re-run (ON CONFLICT DO NOTHING)

INSERT INTO public.sales_daily (date, region, category, revenue, orders) VALUES
('2025-09-01', 'North', 'Electronics', 125000.50, 310),
('2025-09-01', 'South', 'Grocery',      54000.00, 820),
('2025-09-01', 'West',  'Fashion',      40500.00, 190),
('2025-09-02', 'North', 'Electronics', 132500.00, 332),
('2025-09-02', 'West',  'Fashion',      45500.00, 210),
('2025-09-02', 'East',  'Grocery',      62000.00, 870),
-- Extra rows for richer queries
('2025-09-03', 'North', 'Grocery',      48000.00, 640),
('2025-09-03', 'South', 'Electronics', 115000.00, 290),
('2025-09-03', 'East',  'Fashion',      38000.00, 175),
('2025-09-04', 'West',  'Electronics', 142000.00, 360),
('2025-09-04', 'South', 'Fashion',      52000.00, 230),
('2025-09-04', 'North', 'Grocery',      61000.00, 910),
('2025-09-05', 'East',  'Electronics',  98000.00, 245),
('2025-09-05', 'West',  'Grocery',      73000.00, 1020),
('2025-09-05', 'South', 'Fashion',      44500.00, 205)
ON CONFLICT (date, region, category) DO NOTHING;