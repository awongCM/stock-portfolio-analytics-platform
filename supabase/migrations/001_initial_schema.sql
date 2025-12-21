-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Create portfolios table
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create stocks table
CREATE TABLE stocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    exchange VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create stock_prices table (TimescaleDB hypertable)
CREATE TABLE stock_prices (
    id UUID DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL REFERENCES stocks(id),
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20, 6),
    high DECIMAL(20, 6),
    low DECIMAL(20, 6),
    close DECIMAL(20, 6),
    volume BIGINT,
    adjusted_close DECIMAL(20, 6),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (stock_id, timestamp)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('stock_prices', 'timestamp', 
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Create transactions table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    stock_id UUID NOT NULL REFERENCES stocks(id),
    transaction_type VARCHAR(10) CHECK (transaction_type IN ('BUY', 'SELL')),
    quantity DECIMAL(20, 6) NOT NULL,
    price DECIMAL(20, 6) NOT NULL,
    commission DECIMAL(20, 6) DEFAULT 0,
    transaction_date TIMESTAMPTZ NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create portfolio_holdings table (current positions)
CREATE TABLE portfolio_holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    stock_id UUID NOT NULL REFERENCES stocks(id),
    quantity DECIMAL(20, 6) NOT NULL,
    average_cost DECIMAL(20, 6) NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(portfolio_id, stock_id)
);

-- Create portfolio_snapshots table (historical performance)
CREATE TABLE portfolio_snapshots (
    id UUID DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    timestamp TIMESTAMPTZ NOT NULL,
    total_value DECIMAL(20, 2),
    total_cost DECIMAL(20, 2),
    realized_gains DECIMAL(20, 2),
    unrealized_gains DECIMAL(20, 2),
    cash_balance DECIMAL(20, 2),
    PRIMARY KEY (portfolio_id, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable('portfolio_snapshots', 'timestamp',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Create indexes for better query performance
CREATE INDEX idx_stock_prices_stock_id ON stock_prices(stock_id);
CREATE INDEX idx_stock_prices_timestamp ON stock_prices(timestamp DESC);
CREATE INDEX idx_transactions_portfolio_id ON transactions(portfolio_id);
CREATE INDEX idx_transactions_stock_id ON transactions(stock_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date DESC);
CREATE INDEX idx_portfolio_holdings_portfolio_id ON portfolio_holdings(portfolio_id);
CREATE INDEX idx_portfolio_snapshots_portfolio_id ON portfolio_snapshots(portfolio_id);
CREATE INDEX idx_stocks_symbol ON stocks(symbol);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at
CREATE TRIGGER update_portfolios_updated_at BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to update portfolio holdings after transaction
CREATE OR REPLACE FUNCTION update_portfolio_holdings()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.transaction_type = 'BUY' THEN
        INSERT INTO portfolio_holdings (portfolio_id, stock_id, quantity, average_cost)
        VALUES (NEW.portfolio_id, NEW.stock_id, NEW.quantity, NEW.price)
        ON CONFLICT (portfolio_id, stock_id) 
        DO UPDATE SET 
            quantity = portfolio_holdings.quantity + NEW.quantity,
            average_cost = (
                (portfolio_holdings.quantity * portfolio_holdings.average_cost) + 
                (NEW.quantity * NEW.price)
            ) / (portfolio_holdings.quantity + NEW.quantity),
            last_updated = NOW();
    ELSIF NEW.transaction_type = 'SELL' THEN
        UPDATE portfolio_holdings
        SET quantity = quantity - NEW.quantity,
            last_updated = NOW()
        WHERE portfolio_id = NEW.portfolio_id 
        AND stock_id = NEW.stock_id;
        
        -- Remove holding if quantity becomes zero or negative
        DELETE FROM portfolio_holdings
        WHERE portfolio_id = NEW.portfolio_id 
        AND stock_id = NEW.stock_id 
        AND quantity <= 0;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger for automatic portfolio holdings update
CREATE TRIGGER update_holdings_on_transaction 
AFTER INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION update_portfolio_holdings();

-- Insert sample data
INSERT INTO portfolios (name, description) VALUES
    ('Growth Portfolio', 'Focused on high-growth tech stocks'),
    ('Dividend Portfolio', 'Income-generating dividend stocks');

INSERT INTO stocks (symbol, name, exchange, sector, industry) VALUES
    ('AAPL', 'Apple Inc.', 'NASDAQ', 'Technology', 'Consumer Electronics'),
    ('MSFT', 'Microsoft Corporation', 'NASDAQ', 'Technology', 'Software'),
    ('GOOGL', 'Alphabet Inc.', 'NASDAQ', 'Technology', 'Internet Services'),
    ('AMZN', 'Amazon.com Inc.', 'NASDAQ', 'Consumer Cyclical', 'Internet Retail'),
    ('TSLA', 'Tesla Inc.', 'NASDAQ', 'Consumer Cyclical', 'Auto Manufacturers');
