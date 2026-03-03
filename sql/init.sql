-- Create the analytics database schema
-- This file runs automatically on first Postgres startup via docker-entrypoint-initdb.d

CREATE TABLE IF NOT EXISTS public.sales_daily (
    date        DATE            NOT NULL,
    region      TEXT            NOT NULL,
    category    TEXT            NOT NULL,
    revenue     NUMERIC(12,2)   NOT NULL,
    orders      INTEGER         NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    PRIMARY KEY (date, region, category)
);

-- Helpful indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_sales_daily_date     ON public.sales_daily (date);
CREATE INDEX IF NOT EXISTS idx_sales_daily_region   ON public.sales_daily (region);
CREATE INDEX IF NOT EXISTS idx_sales_daily_category ON public.sales_daily (category);