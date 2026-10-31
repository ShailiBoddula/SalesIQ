"""FastAPI application exposing SalesIQ analytics endpoints."""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from backend.ai_service import interpret_question
from backend.analytics import (
    compare_monthly_revenue,
    get_monthly_revenue,
    get_product_revenue,
    get_region_revenue,
    get_total_revenue,
)

app = FastAPI(title="SalesIQ API")


class AskRequest(BaseModel):
    """Request body for the natural-language ask endpoint."""

    question: str


@app.get("/")
def read_root():
    """Welcome endpoint."""
    return {
        "status": "success",
        "question": "Welcome to the SalesIQ Mini AI Business Intelligence Assistant API.",
        "data": {
            "service": "SalesIQ API",
            "version": "0.1.0",
            "endpoints": [
                "/",
                "/analytics/total-revenue",
                "/analytics/products",
                "/analytics/monthly",
                "/analytics/regions",
                "/analytics/compare",
                "/ask"
            ]
        }
    }


@app.get("/analytics/total-revenue")
def total_revenue():
    """Return overall revenue and transaction statistics."""
    try:
        data = get_total_revenue()
    except Exception as exc:  # pragma: no cover - defensive error handling
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute total revenue: {exc}"
        )

    return {
        "status": "success",
        "question": "What is the total revenue?",
        "data": data
    }


@app.get("/analytics/products")
def product_revenue():
    """Return product-wise revenue, sorted from highest to lowest."""
    try:
        data = get_product_revenue()
    except Exception as exc:  # pragma: no cover - defensive error handling
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute product revenue: {exc}"
        )

    return {
        "status": "success",
        "question": "Which product generates the highest revenue?",
        "data": data
    }


@app.get("/analytics/monthly")
def monthly_revenue():
    """Return monthly revenue and month-over-month changes."""
    try:
        data = get_monthly_revenue()
    except Exception as exc:  # pragma: no cover - defensive error handling
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute monthly revenue: {exc}"
        )

    return {
        "status": "success",
        "question": "What is the monthly revenue trend?",
        "data": data
    }


@app.get("/analytics/regions")
def region_revenue():
    """Return region-wise revenue, sorted from highest to lowest."""
    try:
        data = get_region_revenue()
    except Exception as exc:  # pragma: no cover - defensive error handling
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute region revenue: {exc}"
        )

    return {
        "status": "success",
        "question": "Which region has the highest revenue?",
        "data": data
    }


@app.get("/analytics/compare")
def compare_monthly(
    month_1: str = Query(..., description="First month in YYYY-MM format"),
    month_2: str = Query(..., description="Second month in YYYY-MM format"),
):
    """Compare revenue between two months."""
    try:
        data = compare_monthly_revenue(month_1, month_2)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive error handling
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare monthly revenue: {exc}"
        )

    return {
        "status": "success",
        "question": (
            f"How does revenue in {data['month_1']} compare to "
            f"{data['month_2']}?"
        ),
        "data": data
    }


@app.post("/ask")
def ask(request: AskRequest):
    """Answer a natural-language question using Groq intent routing.

    The LLM is used ONLY to classify intent and extract parameters.
    Execution is always delegated to existing, hardcoded analytics
    functions. The LLM never generates or executes SQL.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail="question must not be empty"
        )

    try:
        interpretation = interpret_question(question)
    except ValueError as exc:
        # Covers missing API keys and malformed model output.
        raise HTTPException(
            status_code=503,
            detail=f"Intent interpretation unavailable: {exc}"
        )
    except Exception as exc:  # pragma: no cover - defensive error handling
        raise HTTPException(
            status_code=503,
            detail="Groq API request failed. Please try again later."
        )

    intent = interpretation["intent"]
    parameters = interpretation.get("parameters") or {}

    try:
        if intent == "total_revenue":
            data = get_total_revenue()
        elif intent == "product_revenue":
            data = get_product_revenue()
        elif intent == "monthly_revenue":
            data = get_monthly_revenue()
        elif intent == "region_revenue":
            data = get_region_revenue()
        elif intent == "compare_monthly_revenue":
            data = compare_monthly_revenue(
                parameters["month_1"], parameters["month_2"]
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Sorry, I could not understand your question as a "
                    f"SalesIQ analytics request (intent: {intent})."
                )
            )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive error handling
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute analytics for intent {intent}: {exc}"
        )

    return {
        "status": "success",
        "question": question,
        "intent": intent,
        "data": data
    }
