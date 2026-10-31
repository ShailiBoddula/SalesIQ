import sqlite3
import pytest

from backend.analytics import (
    get_total_revenue,
    get_product_revenue,
    get_monthly_revenue,
    get_region_revenue,
    compare_monthly_revenue,
)


@pytest.fixture
def test_db(tmp_path):
    """Create an isolated SQLite database with controlled test records."""

    db_path = str(tmp_path / "test_sales.db")

    conn = sqlite3.connect(db_path)

    conn.execute("""
        CREATE TABLE sales_transactions (
            transaction_id TEXT PRIMARY KEY,
            order_date TEXT,
            product TEXT NOT NULL,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            sales_channel TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL,
            discount_amount REAL NOT NULL,
            status TEXT NOT NULL,
            revenue_eligible INTEGER NOT NULL,
            exclusion_reason TEXT
        )
    """)

    records = [
        (
            "T001", "2026-01-05", "Product A", "Electronics",
            "North", "Online", 2, 100, 10, "Completed", 1, None
        ),
        (
            "T002", "2026-01-10", "Product B", "Accessories",
            "South", "Retail", 1, 200, 0, "Completed", 1, None
        ),
        (
            "T003", "2026-02-05", "Product A", "Electronics",
            "North", "Online", 1, 100, 0, "Completed", 1, None
        ),
        (
            "T004", "2026-02-12", "Product B", "Accessories",
            "South", "Retail", 3, 50, 5, "Completed", 1, None
        ),
        (
            "T005", "2026-02-15", "Product C", "Electronics",
            "West", "Online", 2, 500, 0, "Returned", 0,
            "returned_transaction"
        ),
        (
            "T006", "2026-02-20", "Product C", "Electronics",
            "East", "Online", 1, None, 0, "Completed", 0,
            "missing_unit_price"
        ),
    ]

    conn.executemany("""
        INSERT INTO sales_transactions VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, records)

    conn.commit()
    conn.close()

    return db_path


def test_total_revenue(test_db):
    result = get_total_revenue(test_db)

    assert result["gross_revenue"] == 650.0
    assert result["total_discounts"] == 15.0
    assert result["net_revenue"] == 635.0
    assert result["eligible_transactions"] == 4
    assert result["excluded_transactions"] == 2
    assert result["units_sold"] == 7


def test_product_revenue_ranking(test_db):
    result = get_product_revenue(test_db)

    assert len(result) == 2
    assert result[0]["product"] == "Product B"
    assert result[0]["net_revenue"] == 345.0
    assert result[1]["product"] == "Product A"
    assert result[1]["net_revenue"] == 290.0


def test_monthly_revenue(test_db):
    result = get_monthly_revenue(test_db)

    assert len(result) == 2

    assert result[0]["month"] == "2026-01"
    assert result[0]["net_revenue"] == 390.0

    assert result[1]["month"] == "2026-02"
    assert result[1]["net_revenue"] == 245.0

    assert result[1]["absolute_change"] == -145.0
    assert result[1]["percentage_change"] == -37.18


def test_region_revenue_ranking(test_db):
    result = get_region_revenue(test_db)

    assert len(result) == 2
    assert result[0]["region"] == "South"
    assert result[0]["net_revenue"] == 345.0
    assert result[1]["region"] == "North"
    assert result[1]["net_revenue"] == 290.0


def test_monthly_comparison(test_db):
    result = compare_monthly_revenue(
        "2026-01", "2026-02", test_db
    )

    assert result["month_1_revenue"] == 390.0
    assert result["month_2_revenue"] == 245.0
    assert result["absolute_change"] == -145.0
    assert result["percentage_change"] == -37.18
    assert result["direction"] == "decrease"


def test_excluded_transactions_do_not_contribute(test_db):
    result = get_total_revenue(test_db)

    # The returned transaction and missing-price transaction
    # must not contribute to revenue or units sold.
    assert result["eligible_transactions"] == 4
    assert result["excluded_transactions"] == 2
    assert result["net_revenue"] == 635.0
    assert result["units_sold"] == 7


def test_zero_previous_month_revenue(test_db):
    result = compare_monthly_revenue(
        "2025-12", "2026-01", test_db
    )

    assert result["month_1_revenue"] == 0.0
    assert result["month_2_revenue"] == 390.0
    assert result["percentage_change"] is None
    assert result["direction"] == "increase"


def test_invalid_month_format(test_db):
    with pytest.raises(ValueError):
        compare_monthly_revenue(
            "January-2026", "2026-02", test_db
        )


def test_empty_database(tmp_path):
    db_path = str(tmp_path / "empty_sales.db")

    conn = sqlite3.connect(db_path)

    conn.execute("""
        CREATE TABLE sales_transactions (
            transaction_id TEXT PRIMARY KEY,
            order_date TEXT,
            product TEXT NOT NULL,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            sales_channel TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL,
            discount_amount REAL NOT NULL,
            status TEXT NOT NULL,
            revenue_eligible INTEGER NOT NULL,
            exclusion_reason TEXT
        )
    """)

    conn.commit()
    conn.close()

    total = get_total_revenue(db_path)

    assert total["net_revenue"] == 0.0
    assert total["eligible_transactions"] == 0
    assert total["excluded_transactions"] == 0

    assert get_product_revenue(db_path) == []
    assert get_monthly_revenue(db_path) == []
    assert get_region_revenue(db_path) == []