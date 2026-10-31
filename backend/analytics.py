import re
import sqlite3

from backend.database import get_connection


def _money(value):
    """Round monetary values to two decimal places."""
    return round(float(value or 0), 2)


def get_total_revenue(db_path=None):
    """Return overall revenue and transaction statistics."""
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COALESCE(SUM(quantity * unit_price), 0) AS gross_revenue,
                COALESCE(SUM(discount_amount), 0) AS total_discounts,
                COALESCE(
                    SUM(quantity * unit_price - discount_amount), 0
                ) AS net_revenue,
                COUNT(*) AS eligible_transactions,
                COALESCE(SUM(quantity), 0) AS units_sold
            FROM sales_transactions
            WHERE revenue_eligible = 1
        """)
        row = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*)
            FROM sales_transactions
            WHERE revenue_eligible = 0
        """)
        excluded_count = cursor.fetchone()[0]

    return {
        "gross_revenue": _money(row["gross_revenue"]),
        "total_discounts": _money(row["total_discounts"]),
        "net_revenue": _money(row["net_revenue"]),
        "eligible_transactions": row["eligible_transactions"],
        "excluded_transactions": excluded_count,
        "units_sold": row["units_sold"]
    }


def get_product_revenue(db_path=None):
    """Return product-wise revenue, sorted from highest to lowest."""
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                product,
                ROUND(
                    SUM(quantity * unit_price - discount_amount), 2
                ) AS net_revenue,
                SUM(quantity) AS units_sold,
                COUNT(*) AS transaction_count
            FROM sales_transactions
            WHERE revenue_eligible = 1
            GROUP BY product
            ORDER BY net_revenue DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_monthly_revenue(db_path=None):
    """Return monthly revenue and month-over-month changes."""
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                strftime('%Y-%m', order_date) AS month,
                ROUND(
                    SUM(quantity * unit_price - discount_amount), 2
                ) AS net_revenue,
                COUNT(*) AS transaction_count,
                SUM(quantity) AS units_sold
            FROM sales_transactions
            WHERE revenue_eligible = 1
            GROUP BY strftime('%Y-%m', order_date)
            ORDER BY month
        """)
        rows = [dict(row) for row in cursor.fetchall()]

    for index, row in enumerate(rows):
        if index == 0:
            row["absolute_change"] = None
            row["percentage_change"] = None
            continue

        previous_revenue = rows[index - 1]["net_revenue"]
        current_revenue = row["net_revenue"]

        row["absolute_change"] = _money(
            current_revenue - previous_revenue
        )

        row["percentage_change"] = (
            round(
                (current_revenue - previous_revenue)
                / previous_revenue * 100,
                2
            )
            if previous_revenue != 0 else None
        )

    return rows


def get_region_revenue(db_path=None):
    """Return region-wise revenue, sorted from highest to lowest."""
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                region,
                ROUND(
                    SUM(quantity * unit_price - discount_amount), 2
                ) AS net_revenue,
                SUM(quantity) AS units_sold,
                COUNT(*) AS transaction_count
            FROM sales_transactions
            WHERE revenue_eligible = 1
            GROUP BY region
            ORDER BY net_revenue DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def compare_monthly_revenue(month_1, month_2, db_path=None):
    """Compare revenue between two months in YYYY-MM format."""
    month_pattern = r"^\d{4}-(0[1-9]|1[0-2])$"

    for month in (month_1, month_2):
        if not isinstance(month, str) or not re.fullmatch(
            month_pattern, month
        ):
            raise ValueError(
                f"Invalid month '{month}'. Expected YYYY-MM format."
            )

    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(
                SUM(quantity * unit_price - discount_amount), 0
            ) AS revenue
            FROM sales_transactions
            WHERE revenue_eligible = 1
              AND strftime('%Y-%m', order_date) = ?
        """, (month_1,))
        revenue_1 = _money(cursor.fetchone()["revenue"])

        cursor.execute("""
            SELECT COALESCE(
                SUM(quantity * unit_price - discount_amount), 0
            ) AS revenue
            FROM sales_transactions
            WHERE revenue_eligible = 1
              AND strftime('%Y-%m', order_date) = ?
        """, (month_2,))
        revenue_2 = _money(cursor.fetchone()["revenue"])

    absolute_change = _money(revenue_2 - revenue_1)

    percentage_change = (
        round(absolute_change / revenue_1 * 100, 2)
        if revenue_1 != 0 else None
    )

    if absolute_change > 0:
        direction = "increase"
    elif absolute_change < 0:
        direction = "decrease"
    else:
        direction = "no change"

    return {
        "month_1": month_1,
        "month_1_revenue": revenue_1,
        "month_2": month_2,
        "month_2_revenue": revenue_2,
        "absolute_change": absolute_change,
        "percentage_change": percentage_change,
        "direction": direction
    }