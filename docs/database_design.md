# SalesIQ - SQLite Database Design

## Why SQLite Was Selected

SQLite is the ideal choice for the SalesIQ MVP for several reasons:

- **Serverless**: No separate database server to install, configure, or run. The entire database is a single file (`data/salesiq.db`), which simplifies deployment and portability.
- **Zero configuration**: Python's built-in `sqlite3` module requires no external drivers or connection strings.
- **Fast for analytical workloads**: For a 51-record dataset (and even hundreds of thousands of records), SQLite query performance is more than sufficient.
- **ACID compliant**: Transactions are supported, ensuring data integrity during imports.
- **Built-in functions**: Date functions like `substr()` enable monthly aggregations directly in SQL.
- **No infrastructure overhead**: Ideal for a recruitment assessment and rapid iteration.

## Table Schema

sql
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
    revenue_eligible INTEGER NOT NULL,
    exclusion_reason TEXT NULL
);

### Column Descriptions

| Column | Type | Constraints | Description |
|---|---|---|---|
| transaction_id | TEXT | PRIMARY KEY | Original Transaction_Id from the CSV |
| order_date | TEXT | | Date stored as YYYY-MM-DD |
| product | TEXT | NOT NULL | Product name |
| category | TEXT | NOT NULL | Product category |
| region | TEXT | NOT NULL | Sales region |
| sales_channel | TEXT | NOT NULL | Online or Retail |
| quantity | INTEGER | NOT NULL | Units sold |
| unit_price | REAL | NULL | Price per unit; NULL when missing |
| discount_amount | REAL | NOT NULL | Discount applied |
| status | TEXT | NOT NULL | Completed or Returned |
| revenue_eligible | INTEGER | NOT NULL | 1 = eligible for revenue calculations, 0 = excluded |
| exclusion_reason | TEXT | NULL | Why the record is excluded (NULL when eligible) |

## Primary Key

`transaction_id` is the PRIMARY KEY. This enforces uniqueness at the database level and enables the idempotent import mechanism (`INSERT OR IGNORE`).

## NULL Handling

- `unit_price` is declared `REAL NULL` to preserve the missing price for TXN0051 as a true SQL NULL.
- `order_date` is allowed to be NULL to handle any future malformed dates.
- `exclusion_reason` is NULL for valid records and populated for excluded ones.
- Missing prices are **never** assumed to be zero. They remain NULL and mark the record ineligible.

## Data Validation

The loader (`backend/data_loader.py`) validates each record before insertion:

1. **transaction_id** — must be non-empty.
2. **order_date** — must match DD-MM-YYYY and be a valid calendar date; converted to YYYY-MM-DD.
3. **product, category, region, sales_channel, status** — must be non-empty.
4. **quantity** — must parse as an integer.
5. **discount_amount** — must parse as an integer.
6. **unit_price** — if present, must parse as a real number.

Invalid records are still inserted (to preserve the original data) but are flagged with `revenue_eligible = 0` and an appropriate `exclusion_reason`.

## Import Strategy

- Uses `pandas.read_csv` to read the source file.
- Each row is validated and transformed.
- Records are inserted with parameterized `INSERT` statements inside a single transaction for performance and atomicity.
- `INSERT OR IGNORE` makes the import **idempotent**: re-running it does not create duplicates.
- The original CSV is never modified.

## Exclusion Policy

A record is excluded from revenue calculations (`revenue_eligible = 0`) when:

| Condition | exclusion_reason | Example |
|---|---|---|
| Status is Returned | `returned_transaction` | TXN0033 |
| Unit price is missing | `missing_unit_price` | TXN0051 |
| Required field missing | `missing_required_field` | (none in current data) |
| Invalid date | `invalid_order_date` | (none in current data) |
| Invalid numeric value | `invalid_quantity` / `invalid_discount_amount` / `invalid_unit_price` | (none in current data) |

Returned transactions are retained in the database but excluded from revenue calculations. Zero-quantity transactions (TXN0034) are treated as valid.

## Indexes

Indexes are created on columns used in common filtering and aggregation queries:

- `idx_sales_transactions_order_date` — on `order_date` (monthly counts)
- `idx_sales_transactions_product` — on `product` (product-level analytics)
- `idx_sales_transactions_region` — on `region` (regional analytics)
- `idx_sales_transactions_status` — on `status` (returned transaction filtering)
- `idx_sales_transactions_revenue_eligible` — on `revenue_eligible` (revenue eligibility filtering)

All indexes use `CREATE INDEX IF NOT EXISTS` so they are safe to re-run.

## Verification Results

After import, the following were confirmed:

1. Total records: 51
2. Distinct transaction IDs: 51
3. Valid records: 49
4. Excluded records: 2 (TXN0033 - returned, TXN0051 - missing price)
5. Returned transactions: 1 (TXN0033)
6. Missing unit prices: 1 (TXN0051, stored as SQL NULL)
7. Zero-quantity transactions: 1 (TXN0034, valid)
8. Monthly counts: Jan 8, Feb 8, Mar 8, Apr 10, May 8, Jun 9
9. Records with NULL values: 1 (TXN0051, unit_price = NULL)
10. Idempotency: Re-importing the same CSV produced 0 duplicates
