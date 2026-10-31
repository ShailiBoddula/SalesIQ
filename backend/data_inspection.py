"""CSV inspection and data quality analysis for SalesIQ.

Reusable functions for inspecting and validating the sales data CSV.
Does NOT modify the original CSV, does NOT fabricate records,
and does NOT assume missing prices are zero.
"""

import os
import re
from datetime import datetime

import pandas as pd


CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sales_data.csv")

DATE_FORMAT = "%d-%m-%Y"
EXPECTED_DATE_REGEX = re.compile(r"^\d{2}-\d{2}-\d{4}$")

NUMERIC_COLUMNS = ["Quantity", "Unit_price", "Discount_amount"]


def load_data(csv_path=CSV_PATH):
    """Load the CSV into a DataFrame without modifying the source file."""
    return pd.read_csv(csv_path)


def basic_summary(df):
    """Return total rows, columns, column names and data types."""
    return {
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "column_names": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }


def head_tail(df, n=5):
    """Return the first and last n records as dictionaries."""
    return {
        "head": df.head(n).to_dict(orient="records"),
        "tail": df.tail(n).to_dict(orient="records"),
    }


def missing_values(df):
    """Count missing values per column."""
    missing = df.isna().sum()
    return {col: int(missing[col]) for col in df.columns}


def duplicate_transaction_ids(df):
    """Return duplicate Transaction_Id values and their count."""
    dup_counts = df["Transaction_Id"].duplicated(keep=False)
    dup_ids = df.loc[dup_counts, "Transaction_Id"].unique().tolist()
    return {
        "duplicate_ids": dup_ids,
        "duplicate_count": int(len(dup_ids)),
        "total_duplicate_rows": int(dup_counts.sum()),
    }


def validate_order_date(df):
    """Validate Order_date against the DD-MM-YYYY format.

    Returns a list of dicts describing each invalid record.
    """
    invalid = []
    for idx, raw in df["Order_date"].astype(str).items():
        is_none = pd.isna(raw) or raw.strip() == "" or raw.lower() == "nan"
        if is_none:
            invalid.append({"row": int(idx), "value": raw, "reason": "missing"})
            continue
        if not EXPECTED_DATE_REGEX.match(raw):
            invalid.append({"row": int(idx), "value": raw, "reason": "format_mismatch"})
            continue
        try:
            datetime.strptime(raw, DATE_FORMAT)
        except ValueError:
            invalid.append({"row": int(idx), "value": raw, "reason": "invalid_calendar_date"})
    return invalid


def numeric_extremes(df):
    """Inspect negative and zero values in numeric columns."""
    result = {}
    for col in NUMERIC_COLUMNS:
        series = pd.to_numeric(df[col], errors="coerce")
        non_missing = series.dropna()
        result[col] = {
            "negative": int((series < 0).sum()),
            "zero": int((series == 0).sum()),
            "missing": int(series.isna().sum()),
            "min": None if non_missing.empty else float(non_missing.min()),
            "max": None if non_missing.empty else float(non_missing.max()),
        }
    return result


def unique_values(df):
    """Return unique values for categorical columns."""
    categorical = ["Product", "Category", "Region", "Sales_channel", "Status"]
    return {col: sorted(df[col].dropna().unique().tolist()) for col in categorical}


def returned_transactions(df):
    """Return records whose Status indicates a return."""
    mask = df["Status"].astype(str).str.strip().str.lower().isin(["returned", "return"])
    return df[mask].to_dict(orient="records")


def missing_or_invalid_prices(df):
    """Return records with missing or non-numeric Unit_price."""
    prices = pd.to_numeric(df["Unit_price"], errors="coerce")
    mask = prices.isna()
    return df[mask].to_dict(orient="records")


def data_quality_statistics(df):
    """Calculate preliminary data-quality statistics."""
    total = len(df)
    missing = int(df.isna().sum().sum())
    dup_ids = duplicate_transaction_ids(df)
    invalid_dates = validate_order_date(df)
    extremes = numeric_extremes(df)
    returned = returned_transactions(df)
    bad_prices = missing_or_invalid_prices(df)

    return {
        "total_records": total,
        "total_missing_cells": missing,
        "missing_cell_percentage": round(100.0 * missing / (total * len(df.columns)), 2),
        "duplicate_transaction_ids": dup_ids["duplicate_count"],
        "duplicate_rows": dup_ids["total_duplicate_rows"],
        "invalid_date_records": len(invalid_dates),
        "negative_quantity": extremes["Quantity"]["negative"],
        "zero_quantity": extremes["Quantity"]["zero"],
        "negative_unit_price": extremes["Unit_price"]["negative"],
        "zero_unit_price": extremes["Unit_price"]["zero"],
        "negative_discount": extremes["Discount_amount"]["negative"],
        "zero_discount": extremes["Discount_amount"]["zero"],
        "returned_transactions": len(returned),
        "records_with_missing_or_invalid_price": len(bad_prices),
    }


def run_full_inspection(csv_path=CSV_PATH):
    """Run every inspection function and return a combined report dict."""
    df = load_data(csv_path)
    return {
        "basic_summary": basic_summary(df),
        "head_tail": head_tail(df),
        "missing_values": missing_values(df),
        "duplicate_transaction_ids": duplicate_transaction_ids(df),
        "invalid_order_dates": validate_order_date(df),
        "numeric_extremes": numeric_extremes(df),
        "unique_values": unique_values(df),
        "returned_transactions": returned_transactions(df),
        "missing_or_invalid_prices": missing_or_invalid_prices(df),
        "data_quality_statistics": data_quality_statistics(df),
    }


if __name__ == "__main__":
    import json

    report = run_full_inspection()
    print(json.dumps(report, indent=2, default=str))