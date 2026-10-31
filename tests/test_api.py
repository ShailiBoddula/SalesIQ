"""API tests for the SalesIQ FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client():
    """Provide a TestClient instance for every test."""
    return TestClient(app)


def _assert_success_response(response):
    """Common assertions shared by every successful endpoint."""
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body["status"] == "success"
    assert isinstance(body["question"], str) and body["question"]
    assert "data" in body
    return body


def test_root_endpoint(client):
    """GET / returns a welcome message with HTTP 200."""
    body = _assert_success_response(client.get("/"))

    assert body["data"]["service"] == "SalesIQ API"
    assert body["data"]["version"] == "0.1.0"


def test_total_revenue_endpoint(client, monkeypatch):
    """GET /analytics/total-revenue returns controlled data via monkeypatch."""
    monkeypatch.setattr(
        "backend.main.get_total_revenue",
        lambda db_path=None: {
            "gross_revenue": 1000.0,
            "total_discounts": 50.0,
            "net_revenue": 950.0,
            "eligible_transactions": 2,
            "excluded_transactions": 1,
            "units_sold": 10,
        },
    )

    body = _assert_success_response(client.get("/analytics/total-revenue"))

    assert body["question"] == "What is the total revenue?"
    assert body["data"]["net_revenue"] == 950.0
    assert body["data"]["eligible_transactions"] == 2


def test_products_endpoint(client, monkeypatch):
    """GET /analytics/products returns product-wise data via monkeypatch."""
    monkeypatch.setattr(
        "backend.main.get_product_revenue",
        lambda db_path=None: [
            {"product": "Widget", "net_revenue": 500.0, "units_sold": 5, "transaction_count": 2}
        ],
    )

    body = _assert_success_response(client.get("/analytics/products"))

    assert body["question"] == "Which product generates the highest revenue?"
    assert body["data"][0]["product"] == "Widget"


def test_monthly_endpoint(client, monkeypatch):
    """GET /analytics/monthly returns monthly trend data via monkeypatch."""
    monkeypatch.setattr(
        "backend.main.get_monthly_revenue",
        lambda db_path=None: [
            {"month": "2026-01", "net_revenue": 100.0, "transaction_count": 1,
             "units_sold": 1, "absolute_change": None, "percentage_change": None}
        ],
    )

    body = _assert_success_response(client.get("/analytics/monthly"))

    assert body["question"] == "What is the monthly revenue trend?"
    assert body["data"][0]["month"] == "2026-01"


def test_regions_endpoint(client, monkeypatch):
    """GET /analytics/regions returns region-wise data via monkeypatch."""
    monkeypatch.setattr(
        "backend.main.get_region_revenue",
        lambda db_path=None: [
            {"region": "North", "net_revenue": 300.0, "units_sold": 3, "transaction_count": 1}
        ],
    )

    body = _assert_success_response(client.get("/analytics/regions"))

    assert body["question"] == "Which region has the highest revenue?"
    assert body["data"][0]["region"] == "North"


def test_compare_endpoint_valid_months(client, monkeypatch):
    """GET /analytics/compare with valid months returns a comparison."""
    monkeypatch.setattr(
        "backend.main.compare_monthly_revenue",
        lambda month_1, month_2, db_path=None: {
            "month_1": month_1,
            "month_1_revenue": 100.0,
            "month_2": month_2,
            "month_2_revenue": 120.0,
            "absolute_change": 20.0,
            "percentage_change": 20.0,
            "direction": "increase",
        },
    )

    body = _assert_success_response(
        client.get("/analytics/compare", params={"month_1": "2026-01", "month_2": "2026-02"})
    )

    assert body["data"]["month_1"] == "2026-01"
    assert body["data"]["month_2"] == "2026-02"
    assert body["data"]["direction"] == "increase"


def test_compare_endpoint_invalid_month_format(client):
    """Invalid month format returns HTTP 400."""
    response = client.get(
        "/analytics/compare", params={"month_1": "bad", "month_2": "2026-02"}
    )

    assert response.status_code == 400
    assert "Invalid month" in response.json()["detail"]


def test_total_revenue_endpoint_handles_exception(client, monkeypatch):
    """Unexpected analytics exceptions produce HTTP 500."""

    def _raise(db_path=None):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("backend.main.get_total_revenue", _raise)

    response = client.get("/analytics/total-revenue")

    assert response.status_code == 500
    assert "Failed to compute total revenue" in response.json()["detail"]


def test_compare_endpoint_handles_exception(client, monkeypatch):
    """Unexpected compare exceptions produce HTTP 500."""

    def _raise(month_1, month_2, db_path=None):
        raise RuntimeError("comparison failed")

    monkeypatch.setattr("backend.main.compare_monthly_revenue", _raise)

    response = client.get(
        "/analytics/compare", params={"month_1": "2026-01", "month_2": "2026-02"}
    )

    assert response.status_code == 500
    assert "Failed to compare monthly revenue" in response.json()["detail"]


# ---------------------------------------------------------------------------
# POST /ask endpoint tests (Groq intent routing)
# ---------------------------------------------------------------------------

def _mock_interpret(monkeypatch, intent, parameters=None):
    """Patch interpret_question to return a fixed intent dict."""
    monkeypatch.setattr(
        "backend.main.interpret_question",
        lambda question: {"intent": intent, "parameters": parameters or {}},
    )


def test_ask_total_revenue(client, monkeypatch):
    """POST /ask routes total_revenue questions to get_total_revenue."""
    _mock_interpret(monkeypatch, "total_revenue")
    monkeypatch.setattr(
        "backend.main.get_total_revenue",
        lambda db_path=None: {
            "gross_revenue": 1000.0,
            "total_discounts": 50.0,
            "net_revenue": 950.0,
            "eligible_transactions": 2,
            "excluded_transactions": 1,
            "units_sold": 10,
        },
    )

    response = client.post("/ask", json={"question": "What is our total revenue?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["question"] == "What is our total revenue?"
    assert body["intent"] == "total_revenue"
    assert body["data"]["net_revenue"] == 950.0


def test_ask_product_revenue(client, monkeypatch):
    """POST /ask routes product_revenue questions to get_product_revenue."""
    _mock_interpret(monkeypatch, "product_revenue")
    monkeypatch.setattr(
        "backend.main.get_product_revenue",
        lambda db_path=None: [
            {"product": "Widget", "net_revenue": 500.0, "units_sold": 5, "transaction_count": 2}
        ],
    )

    response = client.post("/ask", json={"question": "Which product generated the highest revenue?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["intent"] == "product_revenue"
    assert body["data"][0]["product"] == "Widget"


def test_ask_monthly_revenue(client, monkeypatch):
    """POST /ask routes monthly_revenue questions to get_monthly_revenue."""
    _mock_interpret(monkeypatch, "monthly_revenue")
    monkeypatch.setattr(
        "backend.main.get_monthly_revenue",
        lambda db_path=None: [
            {"month": "2026-01", "net_revenue": 100.0, "transaction_count": 1,
             "units_sold": 1, "absolute_change": None, "percentage_change": None}
        ],
    )

    response = client.post("/ask", json={"question": "Show me the monthly revenue trend."})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["intent"] == "monthly_revenue"
    assert body["data"][0]["month"] == "2026-01"


def test_ask_region_revenue(client, monkeypatch):
    """POST /ask routes region_revenue questions to get_region_revenue."""
    _mock_interpret(monkeypatch, "region_revenue")
    monkeypatch.setattr(
        "backend.main.get_region_revenue",
        lambda db_path=None: [
            {"region": "North", "net_revenue": 300.0, "units_sold": 3, "transaction_count": 1}
        ],
    )

    response = client.post("/ask", json={"question": "Which region has the highest sales?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["intent"] == "region_revenue"
    assert body["data"][0]["region"] == "North"


def test_ask_compare_monthly(client, monkeypatch):
    """POST /ask routes compare_monthly_revenue with validated months."""
    _mock_interpret(
        monkeypatch,
        "compare_monthly_revenue",
        parameters={"month_1": "2026-01", "month_2": "2026-02"},
    )
    monkeypatch.setattr(
        "backend.main.compare_monthly_revenue",
        lambda month_1, month_2, db_path=None: {
            "month_1": month_1,
            "month_1_revenue": 100.0,
            "month_2": month_2,
            "month_2_revenue": 120.0,
            "absolute_change": 20.0,
            "percentage_change": 20.0,
            "direction": "increase",
        },
    )

    response = client.post(
        "/ask",
        json={"question": "Compare revenue between January 2026 and February 2026."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["intent"] == "compare_monthly_revenue"
    assert body["data"]["month_1"] == "2026-01"
    assert body["data"]["month_2"] == "2026-02"


def test_ask_unsupported_intent(client, monkeypatch):
    """POST /ask returns HTTP 400 for unsupported intents."""
    _mock_interpret(monkeypatch, "unsupported")

    response = client.post("/ask", json={"question": "What is the weather in Hyderabad?"})

    assert response.status_code == 400
    assert "could not understand" in response.json()["detail"]


def test_ask_empty_question(client):
    """POST /ask returns HTTP 400 for empty questions."""
    response = client.post("/ask", json={"question": "   "})

    assert response.status_code == 400
    assert "must not be empty" in response.json()["detail"]


def test_ask_groq_service_failure(client, monkeypatch):
    """POST /ask returns HTTP 503 when the Groq service fails."""

    def _raise(question):
        raise ValueError("GROQ_API_KEY is not set")

    monkeypatch.setattr("backend.main.interpret_question", _raise)

    response = client.post("/ask", json={"question": "What is our total revenue?"})

    assert response.status_code == 503
    assert "Intent interpretation unavailable" in response.json()["detail"]
