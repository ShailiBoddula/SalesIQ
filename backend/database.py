"""SQLite database creation and connection management for SalesIQ.

Uses Python's built-in sqlite3 library.
Creates the sales_transactions table with the required schema
and supporting indexes.
"""

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "salesiq.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sales_transactions (
    transaction_id   TEXT PRIMARY KEY,
    order_date       TEXT,
    product          TEXT NOT NULL,
    category         TEXT NOT NULL,
    region           TEXT NOT NULL,
    sales_channel    TEXT NOT NULL,
    quantity         INTEGER NOT NULL,
    unit_price       REAL NULL,
    discount_amount  REAL NOT NULL,
    status           TEXT NOT NULL,
    revenue_eligible  INTEGER NOT NULL,
    exclusion_reason  TEXT NULL
)
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_sales_transactions_order_date ON sales_transactions(order_date)",
    "CREATE INDEX IF NOT EXISTS idx_sales_transactions_product ON sales_transactions(product)",
    "CREATE INDEX IF NOT EXISTS idx_sales_transactions_region ON sales_transactions(region)",
    "CREATE INDEX IF NOT EXISTS idx_sales_transactions_status ON sales_transactions(status)",
    "CREATE INDEX IF NOT EXISTS idx_sales_transactions_revenue_eligible ON sales_transactions(revenue_eligible)",
]


def get_db_path():
    """Return the absolute path to the SQLite database file."""
    return os.path.abspath(DB_PATH)


def create_connection(db_path=None):
    """Create and return a connection to the SQLite database."""
    if db_path is None:
        db_path = get_db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn):
    """Create the sales_transactions table and indexes if they do not exist."""
    conn.execute(CREATE_TABLE_SQL)
    for idx_sql in CREATE_INDEXES_SQL:
        conn.execute(idx_sql)
    conn.commit()


def reset_database(db_path=None):
    """Drop the table and recreate it. Useful for a clean re-import."""
    if db_path is None:
        db_path = get_db_path()
    conn = create_connection(db_path)
    try:
        conn.execute("DROP TABLE IF EXISTS sales_transactions")
        conn.commit()
        create_tables(conn)
    finally:
        conn.close()


@contextmanager
def get_connection(db_path=None):
    """Context manager that yields a connection and closes it on exit."""
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    conn = create_connection()
    create_tables(conn)
    print("Database created at:", get_db_path())
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sales_transactions'"
    )
    print("Table exists:", cursor.fetchone() is not None)
    conn.close()