"""DDL for the fintech schema."""

from psycopg import Connection

_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    external_user_id UUID NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    tax_id TEXT NOT NULL,
    address_line1 TEXT NOT NULL,
    address_line2 TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country TEXT NOT NULL,
    kyc_status TEXT NOT NULL,
    kyc_document BYTEA,
    risk_score NUMERIC(5, 2) NOT NULL,
    device_fingerprint JSONB,
    signup_ip INET,
    created_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id BIGSERIAL PRIMARY KEY,
    external_account_id UUID NOT NULL UNIQUE,
    user_id BIGINT NOT NULL REFERENCES users(id),
    card_number_masked TEXT NOT NULL,
    card_number_token TEXT NOT NULL,
    card_network TEXT NOT NULL,
    credit_limit NUMERIC(12, 2) NOT NULL,
    current_balance NUMERIC(12, 2) NOT NULL,
    billing_cycle_day SMALLINT NOT NULL,
    account_status TEXT NOT NULL,
    feature_flags BIT(16) NOT NULL,
    opened_at DATE NOT NULL,
    interest_rate NUMERIC(5, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    retrieval_reference_number TEXT NOT NULL UNIQUE,
    system_trace_audit_number TEXT NOT NULL,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    message_type_indicator TEXT NOT NULL,
    processing_code TEXT NOT NULL,
    transaction_amount NUMERIC(12, 2) NOT NULL,
    currency_code TEXT NOT NULL,
    merchant_name TEXT NOT NULL,
    merchant_category_code TEXT NOT NULL,
    terminal_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    response_code TEXT NOT NULL,
    transaction_timestamp TIMESTAMPTZ NOT NULL,
    posted_timestamp TIMESTAMPTZ NOT NULL,
    channel TEXT NOT NULL,
    device_fingerprint JSONB,
    geolocation JSONB,
    is_international BOOLEAN NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS reward_events (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    transaction_id BIGINT REFERENCES transactions(id),
    reward_type TEXT NOT NULL,
    points_earned NUMERIC(10, 2) NOT NULL,
    cash_value NUMERIC(10, 2) NOT NULL,
    redeemed BOOLEAN NOT NULL,
    redeemed_at TIMESTAMPTZ,
    expiry_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS repayments (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    due_date DATE NOT NULL,
    amount_due NUMERIC(12, 2) NOT NULL,
    amount_paid NUMERIC(12, 2) NOT NULL,
    payment_method TEXT NOT NULL,
    payment_reference TEXT NOT NULL,
    paid_at TIMESTAMPTZ,
    late_fee NUMERIC(10, 2) NOT NULL,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_reward_events_account_id ON reward_events(account_id);
CREATE INDEX IF NOT EXISTS idx_repayments_account_id ON repayments(account_id);
"""


def create_schema(conn: Connection) -> None:
    conn.execute(_DDL)
    conn.commit()


def drop_schema(conn: Connection) -> None:
    conn.execute(
        "DROP TABLE IF EXISTS reward_events, repayments, transactions, accounts, users CASCADE"
    )
    conn.commit()
