# SalesIQ — AI Development Report

## 1. AI tools used
- **ChatGPT:** Used to understand the assignment, plan the architecture, explain design choices, generate/review code, troubleshoot errors and prepare documentation.
- **Kilo Code:** Used in the VS Code workflow for code-generation and project-editing assistance when its tool execution was available.
- **Groq API with `openai/gpt-oss-120b`:** Integrated into the application to interpret natural-language questions and classify them into supported analytics intents.

ChatGPT and Kilo Code were development assistants. Groq is the AI service used by the running application.

## 2. How AI was used
AI assistance was used iteratively to break down requirements, plan the Python/FastAPI/SQLite/Streamlit architecture, inspect data quality, design database and analytics code, implement API endpoints, integrate structured intent interpretation, build the UI, create tests, and troubleshoot issues. Generated code was reviewed and tested rather than assumed correct.

The application uses deterministic SQL analytics for calculations. The LLM interprets the question but does not calculate revenue or execute generated SQL.

## 3. Problems encountered
- **Environment/dependencies:** A project virtual environment was established and dependencies installed there.
- **Data quality:** The CSV contained a returned transaction and a missing unit price. These rows were preserved but excluded from revenue using an eligibility flag and reason.
- **SQLite row access:** Analytics needed dictionary-like column access; connections were configured with `sqlite3.Row`.
- **Groq model availability:** An initial model identifier returned model-not-found. The integration was changed to `openai/gpt-oss-120b`, and intent smoke tests then succeeded.
- **Frontend/backend connectivity:** The UI initially could not retrieve data because FastAPI was not running. Running backend and frontend in separate terminals resolved this.
- **Development tool execution:** Some Kilo Code write/command operations failed due to missing required arguments; affected files were created or edited manually and tested.

## 4. Debugging approach
- Verified the active Python interpreter and installed packages.
- Inspected CSV quality and database import results.
- Checked analytics outputs and used automated tests.
- Tested endpoints through FastAPI's `/docs` and the test client.
- Ran live Groq smoke tests for supported and unsupported questions.
- Checked backend/frontend terminal output to diagnose connectivity.
- Used Pytest to test analytics and API behavior without depending on live Groq calls.

The last recorded development test run reported 26 passing tests. Rerun the suite on the final repository before submission.

## 5. What could be improved with another day
- Add more approved intents, such as sales-channel and category analysis.
- Support conversational follow-up questions.
- Strengthen schema validation for model output.
- Add structured logging, caching and configurable deployment settings.
- Add authentication and authorization for multi-user deployment.
- Expand tests for malformed model responses, service outages and additional data-quality edge cases.
- Improve explanations and visual presentation of supporting figures.

## 6. Key design decision
A text-to-SQL approach was not used. The model classifies questions into a fixed set of allowed intents, and the backend routes each intent to a predefined analytics function. This avoids executing arbitrary model-generated SQL and keeps calculations deterministic and testable.
