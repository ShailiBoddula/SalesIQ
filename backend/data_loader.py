"""CSV to SQLite data loader for SalesIQ.

Reads data/sales_data.csv, validates each record, and inserts it into
the SQLite database using parameterized INSERT statements inside a
single transaction. The import is idempotent: re-running it does not
duplicate records.
"""

import os
import re
from datetime import datetime

import pandas as pd

from backend.database import create_connection, create_tables, get_db_path

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sales_data.csv")

DATE_FORMAT = "%d-%m-%Y"
DATE_OUTPUT_FORMAT = "%Y-%m-%d"
DATE_REGEX = re.compile(r"^\d{2}-\d{2}-\d{4}$")


def parse_order_date(raw):
    """Parse a DD-MM-YYYY date string and return YYYY-MM-DD or None."""
    if pd.isna(raw):
        return None
    raw = str(raw).strip()
    if not raw or not DATE_REGEX.match(raw):
        return None
    try:
        return datetime.strptime(raw, DATE_FORMAT).strftime(DATE_OUTPUT_FORMAT)
    except ValueError:
        return None


def parse_integer(raw):
    """Parse an integer value. Returns (value, is_valid)."""
    if pd.isna(raw):
        return None, False
    try:
        return int(float(raw)), True
    except (ValueError, TypeError):
        return None, False


def parse_real(raw):
    """Parse a real/float value. Returns (value, is_valid)."""
    if pd.isna(raw):
        return None, True
    try:
        return float(raw), True
    except (ValueError, TypeError):
        return None, False


def validate_record(row):
    """Validate a single record and determine its eligibility.

    Returns a dict with all fields plus revenue_eligible and exclusion_reason.
    """
    transaction_id = str(row.get("Transaction_Id", "")).strip()
    order_date = parse_order_date(row.get("Order_date"))
    product = str(row.get("Product", "")).strip()
    category = str(row.get("Category", "")).strip()
    region = str(row.get("Region", "")).strip()
    sales_channel = str(row.get("Sales_channel", "")).strip()
    status = str(row.get("Status", "")).strip()

    quantity, qty_valid = parse_integer(row.get("Quantity"))
    unit_price, price_valid = parse_real(row.get("Unit_price"))
    discount_amount, disc_valid = parse_integer(row.get("Discount_amount"))

    exclusion_reason = None

    if not transaction_id:
        exclusion_reason = "missing_transaction_id"
    if order_date is None:
        exclusion_reason = "invalid_order_date"
    if not product or not category or not region or not sales_channel or not status:
        exclusion_reason = "missing_required_field"
    if not qty_valid or quantity is None:
        exclusion_reason = "invalid_quantity"
    if not disc_valid or discount_amount is None:
        exclusion_reason = "invalid_discount_amount"
    if unit_price is not None and not price_valid:
        exclusion_reason = "invalid_unit_price"

    # Business exclusion rules (applied only when basic validation passed)
    if exclusion_reason is None:
        if status.lower() in ("returned", "return"):
            exclusion_reason = "returned_transaction"
        elif unit_price is None:
            exclusion_reason = "missing_unit_price"

    revenue_eligible = 1 if exclusion_reason is None else 0

    return {
        "transaction_id": transaction_id,
        "order_date": order_date,
        "product": product,
        "category": category,
        "region": region,
        "sales_channel": sales_channel,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_amount": discount_amount,
        "status": status,
        "revenue_eligible": revenue_eligible,
        "exclusion_reason": exclusion_reason,
    }


def load_and_import(db_path=None, reset=False):
    """Load the CSV and import all records into SQLite.

    Idempotent: uses INSERT OR IGNORE so re-running does not duplicate
    records. Pass reset=True to drop and recreate the table first.
    """
    if db_path is None:
        db_path = get_db_path()

    df = pd.read_csv(CSV_PATH)
    conn = create_connection(db_path)
    try:
        create_tables(conn)

        if reset:
            conn.execute("DELETE FROM sales_transactions")

        inserted = 0
        skipped_duplicates = 0
        seen_ids = set()

        for _, row in df.iterrows():
            record = validate_record(row)
            tid = record["transaction_id"]

            if tid in seen_ids:
                skipped_duplicates += 1
                continue
            seen_ids.add(tid)

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO sales_transactions
                (transaction_id, order_date, product, category, region,
                 sales_channel, quantity, unit_price, discount_amount,
                 status, revenue_eligible, exclusion_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["transaction_id"],
                    record["order_date"],
                    record["product"],
                    record["category"],
                    record["region"],
                    record["sales_channel"],
                    record["quantity"],
                    record["unit_price"],
                    record["discount_amount"],
                    record["status"],
                    record["revenue_eligible"],
                    record["exclusion_reason"],
                ),
            )
            if cursor.rowcount and cursor.rowcount > 0:
                inserted += 1
            else:
                skipped_duplicates += 1

        conn.commit()
        return {
            "csv_rows": int(len(df)),
            "inserted": inserted,
            "skipped_duplicates": skipped_duplicates,
            "db_path": db_path,
        }
    finally:
        conn.close()


def import_summary(db_path=None):
    """Return summary counts from the database."""
    if db_path is None:
        db_path = get_db_path()
    conn = create_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM sales_transactions").fetchone()[0]
        eligible = conn.execute("SELECT COUNT(*) FROM sales_transactions WHERE revenue_eligible = 1").fetchone()[0]
        excluded = conn.execute("SELECT COUNT(*) FROM sales_transactions WHERE revenue_eligible = 0").fetchone()[0]
        distinct_ids = conn.execute("SELECT COUNT(DISTINCT transaction_id) FROM sales_transactions").fetchone()[0]
        returned = conn.execute("SELECT COUNT(*) FROM sales_transactions WHERE status = 'Returned'").fetchone()[0]
        missing_price = conn.execute("SELECT COUNT(*) FROM sales_transactions WHERE unit_price IS NULL").fetchone()[0]
        zero_qty = conn.execute("SELECT COUNT(*) FROM sales_transactions WHERE quantity = 0").fetchone()[0]
        return {
            "total_records": total,
            "revenue_eligible_records": eligible,
            "excluded_records": excluded,
            "distinct_transaction_ids": distinct_ids,
            "returned_transactions": returned,
            "missing_unit_prices": missing_price,
            "zero_quantity_transactions": zero_qty,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    result = load_and_import()
    print("Import result:", result)
    print("Summary:", import_summary())