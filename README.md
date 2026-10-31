# SalesIQ — Mini AI Business Intelligence Assistant

SalesIQ is an AI-powered business intelligence assistant that allows users to ask natural-language questions about sales data and receive structured answers backed by actual SQLite database queries.

The application uses an LLM to understand the user's question and identify the appropriate analytical operation. The actual calculations are performed using deterministic SQL queries, ensuring that answers are grounded in the stored sales data.

## Features

- Ask questions about sales data using natural language.
- Calculate total gross revenue, discounts, and net revenue.
- Identify products generating the highest revenue.
- Analyze monthly revenue trends.
- Compare revenue between two months.
- Identify the region generating the highest sales.
- Display relevant figures and charts through a Streamlit interface.
- Handle unsupported questions and invalid inputs.
- Use validated, allowlisted AI intents instead of executing AI-generated SQL.
- Import CSV records into SQLite with duplicate protection.
- Include automated tests for analytics and API behavior.

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Backend API | FastAPI |
| Frontend | Streamlit |
| Database | SQLite |
| Data Processing | Pandas |
| AI Integration | Groq API |
| AI Model | openai/gpt-oss-120b |
| Data Visualization | Plotly |
| Testing | Pytest, HTTPX |

## Project Structure

```text
SalesIQ/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── data_loader.py
│   ├── data_inspection.py
│   ├── analytics.py
│   └── ai_service.py
│
├── frontend/
│   └── app.py
│
├── data/
│   └── sales_data.csv
│
├── docs/
│   ├── architecture.md
│   ├── database_design.md
│   ├── data_quality_report.md
│   └── ai_development_report.md
│
├── tests/
│   ├── test_analytics.py
│   └── test_api.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

The SQLite database (`data/salesiq.db`), environment file (`.env`), and virtual environment are excluded from version control.

## Prerequisites

- Python 3.10 or later
- Git
- A Groq API key

## Installation and Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd SalesIQ
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure the environment variable

Create a `.env` file in the project root.

Add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key
```

You can use `.env.example` as a reference. Never commit your actual `.env` file or expose your API key.

### 5. Initialize the database and import CSV data

The source dataset is located at `data/sales_data.csv`.

Run the following command from the project root:

```powershell
python -m backend.data_loader
```

This command creates the SQLite database, validates the CSV records, and imports them into the `sales_transactions` table.

The import process uses parameterized SQL statements and duplicate protection, making repeated imports safe.

### 6. Start the FastAPI backend

Open a terminal and run:

```powershell
python -m uvicorn backend.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 7. Start the Streamlit frontend

Open another terminal, activate the virtual environment, and run:

```powershell
python -m streamlit run frontend/app.py
```

Open the URL displayed in the terminal, normally:

```text
http://localhost:8501
```

## Supported Questions

SalesIQ supports the following analytical operations:

| Example Question | Analytical Operation |
|---|---|
| What is the total revenue? | Total revenue |
| Which product generated the highest revenue? | Product revenue ranking |
| What is the monthly revenue trend? | Monthly revenue analysis |
| Which region generated the highest sales? | Regional revenue analysis |
| How did revenue change between January and February 2026? | Monthly comparison |

The application also handles unsupported questions by returning an appropriate response rather than inventing an answer.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API health information |
| GET | `/analytics/total-revenue` | Total revenue summary |
| GET | `/analytics/products` | Product-wise revenue |
| GET | `/analytics/monthly` | Monthly revenue analysis |
| GET | `/analytics/regions` | Region-wise revenue |
| GET | `/analytics/compare` | Compare two months |
| POST | `/ask` | Process a natural-language question |

For interactive API testing, visit `/docs` after starting the backend.

## Architecture

The application follows a simple layered architecture:

1. **Streamlit frontend:** Accepts natural-language questions and displays analytical results.
2. **FastAPI backend:** Receives requests and coordinates the processing workflow.
3. **AI interpretation layer:** Uses the Groq API to classify questions into predefined analytical intents.
4. **Validation and routing:** Checks the returned intent against an allowlist and routes the request to the appropriate function.
5. **Analytics engine:** Executes predefined, parameterized SQL queries.
6. **SQLite database:** Stores validated sales transaction records.
7. **Response layer:** Returns structured results to the frontend for display.

The LLM interprets the question but does not generate or execute SQL queries. This keeps database access controlled and predictable.

For more details, see [`docs/architecture.md`](docs/architecture.md).

## Revenue Calculation and Data Handling

SalesIQ uses the following calculation:

**Net Revenue = (Quantity × Unit Price) − Discount Amount**

The implementation follows these data-handling rules:

- Completed transactions with valid prices are included in revenue calculations.
- Returned transactions are excluded from revenue calculations.
- Transactions with missing unit prices are excluded from revenue calculations.
- Zero-quantity transactions are retained as eligible records, contributing zero revenue.
- Excluded records remain stored in the database with an exclusion reason.
- Missing prices are not silently treated as zero.

These rules ensure that revenue calculations use eligible records only.

## Testing

Automated tests cover the analytics functions and API endpoints.

Run the test suite from the project root:

```powershell
python -m pytest -v
```

The tests cover:

- Total revenue calculations.
- Product revenue ranking.
- Monthly revenue analysis.
- Regional revenue ranking.
- Monthly revenue comparisons.
- Excluded transactions.
- Zero previous-month revenue.
- Invalid month inputs.
- Empty database behavior.
- API validation and error handling.
- AI intent routing using mocked responses.

## AI Integration and Safety

SalesIQ uses an LLM for natural-language understanding rather than unrestricted SQL generation.

The AI layer returns a structured intent from a predefined list:

- `total_revenue`
- `product_revenue`
- `monthly_revenue`
- `region_revenue`
- `compare_monthly_revenue`
- `unsupported`

The backend validates the intent and uses the corresponding analytical function.

This design helps prevent arbitrary SQL execution, limits database access to predefined operations, and ensures that numerical answers are calculated directly from database records.

## Documentation

Additional project documentation is available in the `docs/` directory:

- **Architecture:** Application components and request flow.
- **Database Design:** Database schema and storage decisions.
- **Data Quality Report:** Dataset inspection and validation findings.
- **AI Development Report:** AI tools used, implementation challenges, debugging, and possible improvements.

## Limitations and Future Improvements

- The current application supports a predefined set of analytical question types.
- The AI interpretation layer depends on the availability of the Groq API.
- The application is designed as a mini business intelligence prototype, not a production-scale analytics platform.
- Future improvements could include additional analytical operations, more flexible date filtering, improved visualizations, and broader data validation.

## Author

**SalesIQ — Mini AI Business Intelligence Assistant**

Developed as a technical assessment project for RSG Research Private Limited.