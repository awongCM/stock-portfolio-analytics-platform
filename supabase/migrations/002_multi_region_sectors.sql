-- Multi-region sector dimensions and FX support (POC)
-- Extends stocks with GICS sector taxonomy and APAC market metadata

-- Reference: APAC markets
CREATE TABLE IF NOT EXISTS markets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    country_code CHAR(2) NOT NULL,
    exchange_mic VARCHAR(10),
    quote_currency CHAR(3) NOT NULL,
    yahoo_suffix VARCHAR(5),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reference: 11 standard GICS sectors
CREATE TABLE IF NOT EXISTS gics_sectors (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    display_order SMALLINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily FX rates for multi-currency reporting
CREATE TABLE IF NOT EXISTS exchange_rates (
    id UUID DEFAULT uuid_generate_v4(),
    base_currency CHAR(3) NOT NULL,
    quote_currency CHAR(3) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    rate DECIMAL(20, 8) NOT NULL,
    source VARCHAR(50) DEFAULT 'yfinance',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (base_currency, quote_currency, timestamp)
);

SELECT create_hypertable(
    'exchange_rates', 'timestamp',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Extend stocks with region/sector dimensions
ALTER TABLE stocks
    ADD COLUMN IF NOT EXISTS country_code CHAR(2),
    ADD COLUMN IF NOT EXISTS quote_currency CHAR(3),
    ADD COLUMN IF NOT EXISTS gics_sector_id INTEGER REFERENCES gics_sectors(id),
    ADD COLUMN IF NOT EXISTS market_id INTEGER REFERENCES markets(id),
    ADD COLUMN IF NOT EXISTS gics_sector_override VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_stocks_gics_sector_id ON stocks(gics_sector_id);
CREATE INDEX IF NOT EXISTS idx_stocks_market_id ON stocks(market_id);
CREATE INDEX IF NOT EXISTS idx_stocks_country_code ON stocks(country_code);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_currencies ON exchange_rates(base_currency, quote_currency);

-- Seed GICS sectors (11 standard)
INSERT INTO gics_sectors (code, name, display_order) VALUES
    ('energy', 'Energy', 1),
    ('materials', 'Materials', 2),
    ('industrials', 'Industrials', 3),
    ('utilities', 'Utilities', 4),
    ('healthcare', 'Healthcare', 5),
    ('financials', 'Financials', 6),
    ('consumer_discretionary', 'Consumer Discretionary', 7),
    ('consumer_staples', 'Consumer Staples', 8),
    ('information_technology', 'Information Technology', 9),
    ('communication_services', 'Communication Services', 10),
    ('real_estate', 'Real Estate', 11)
ON CONFLICT (code) DO NOTHING;

-- Seed APAC markets
INSERT INTO markets (code, name, country_code, exchange_mic, quote_currency, yahoo_suffix) VALUES
    ('ASX', 'Australian Securities Exchange', 'AU', 'XASX', 'AUD', '.AX'),
    ('NZX', 'New Zealand Exchange', 'NZ', 'XNZE', 'NZD', '.NZ'),
    ('BURSA', 'Bursa Malaysia', 'MY', 'XKLS', 'MYR', '.KL'),
    ('SGX', 'Singapore Exchange', 'SG', 'XSES', 'SGD', '.SI')
ON CONFLICT (code) DO NOTHING;

-- Continuous aggregate: daily OHLCV per stock
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_prices_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS bucket,
    stock_id,
    FIRST(open, timestamp) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, timestamp) AS close,
    SUM(volume) AS volume
FROM stock_prices
GROUP BY bucket, stock_id
WITH NO DATA;

-- Refresh policy: roll up daily bars once per day
SELECT add_continuous_aggregate_policy(
    'stock_prices_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Index for sector/region joins on securities
CREATE INDEX IF NOT EXISTS idx_exchange_rates_timestamp ON exchange_rates(timestamp DESC);
