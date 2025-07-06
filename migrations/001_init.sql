CREATE TABLE IF NOT EXISTS payments (
    correlation_id UUID PRIMARY KEY,
    amount NUMERIC(18,2) NOT NULL,
    processor VARCHAR(10) NOT NULL, -- 'default' | 'fallback'
    requested_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_payments_requested_at
    ON payments (requested_at);
