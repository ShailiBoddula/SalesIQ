
import streamlit as st
import requests
import plotly.express as px

# --------------------------------------------------
# Configuration
# --------------------------------------------------

API_BASE_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 15

st.set_page_config(
    page_title="SalesIQ | Business Intelligence",
    page_icon="📊",
    layout="wide"
)

# --------------------------------------------------
# Session State
# --------------------------------------------------

if "answer" not in st.session_state:
    st.session_state.answer = None

# --------------------------------------------------
# API Helpers
# --------------------------------------------------

def ask_question(question):
    """Send a natural-language question to the AI endpoint."""

    try:
        response = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question},
            timeout=60
        )

        if response.status_code == 400:
            detail = response.json().get(
                "detail", "Unsupported question."
            )
            st.warning(detail)
            return None

        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        st.error("Unable to connect to SalesIQ. Please try again later.")

    except requests.exceptions.Timeout:
        st.error("AI request timed out. Please try again.")

    except requests.exceptions.HTTPError:
        st.error("The backend could not process your question.")

    except requests.exceptions.RequestException:
        st.error("Unexpected communication error.")

    return None


# --------------------------------------------------
# Answer Rendering
# --------------------------------------------------

def show_total_revenue(data):
    st.subheader("💰 Revenue Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Net Revenue",
        f"₹{data['net_revenue']:,.2f}"
    )

    col2.metric(
        "Gross Revenue",
        f"₹{data['gross_revenue']:,.2f}"
    )

    col3.metric(
        "Total Discounts",
        f"₹{data['total_discounts']:,.2f}"
    )

    col4, col5, col6 = st.columns(3)

    col4.metric(
        "Eligible Transactions",
        data["eligible_transactions"]
    )

    col5.metric(
        "Excluded Transactions",
        data["excluded_transactions"]
    )

    col6.metric(
        "Units Sold",
        data["units_sold"]
    )


def show_product_revenue(data):
    st.subheader("🏆 Product Revenue Analysis")

    if not data:
        st.info("No product revenue data available.")
        return

    top_product = data[0]

    col1, col2 = st.columns(2)

    col1.metric(
        "Highest Revenue Product",
        top_product["product"]
    )

    col2.metric(
        "Revenue Generated",
        f"₹{top_product['net_revenue']:,.2f}"
    )

    fig = px.bar(
        data,
        x="net_revenue",
        y="product",
        orientation="h",
        title="Revenue by Product",
        labels={
            "net_revenue": "Revenue (₹)",
            "product": "Product"
        }
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True)


def show_monthly_revenue(data):
    st.subheader("📅 Monthly Revenue Trend")

    if not data:
        st.info("No monthly revenue data available.")
        return

    fig = px.bar(
        data,
        x="month",
        y="net_revenue",
        title="Monthly Net Revenue",
        labels={
            "month": "Month",
            "net_revenue": "Revenue (₹)"
        },
        text_auto=".2s"
    )

    fig.update_layout(
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True)


def show_region_revenue(data):
    st.subheader("🌍 Regional Revenue Analysis")

    if not data:
        st.info("No regional revenue data available.")
        return

    top_region = data[0]

    col1, col2 = st.columns(2)

    col1.metric(
        "Highest Revenue Region",
        top_region["region"]
    )

    col2.metric(
        "Revenue Generated",
        f"₹{top_region['net_revenue']:,.2f}"
    )

    fig = px.pie(
        data,
        names="region",
        values="net_revenue",
        title="Revenue Distribution by Region",
        hole=0.4
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(data, use_container_width=True)


def show_monthly_comparison(data):
    st.subheader("📊 Monthly Revenue Comparison")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        data["month_1"],
        f"₹{data['month_1_revenue']:,.2f}"
    )

    col2.metric(
        data["month_2"],
        f"₹{data['month_2_revenue']:,.2f}"
    )

    change = data["absolute_change"]
    percentage = data["percentage_change"]

    col3.metric(
        "Revenue Change",
        f"₹{change:,.2f}",
        delta=(
            f"{percentage:.2f}%"
            if percentage is not None else "N/A"
        )
    )

    st.info(
        f"Revenue direction: {data['direction'].title()}"
    )


def display_answer(answer):
    """Display only the analytics relevant to the detected intent."""

    intent = answer.get("intent")
    data = answer.get("data")

    st.success("Analysis completed successfully.")

    st.write(f"**Your question:** {answer.get('question', '')}")

    if intent == "total_revenue":
        show_total_revenue(data)

    elif intent == "product_revenue":
        show_product_revenue(data)

    elif intent == "monthly_revenue":
        show_monthly_revenue(data)

    elif intent == "region_revenue":
        show_region_revenue(data)

    elif intent == "compare_monthly_revenue":
        show_monthly_comparison(data)

    else:
        st.warning(
            "SalesIQ could not identify a supported business analysis."
        )


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

st.sidebar.title("📊 SalesIQ")
st.sidebar.caption("AI-Powered Business Intelligence")
st.sidebar.divider()

st.sidebar.subheader("About")

st.sidebar.write(
    "Explore sales data through natural-language questions "
    "and discover meaningful business insights."
)

st.sidebar.divider()

st.sidebar.subheader("💡 Example Questions")

examples = [
    "What is our total revenue?",
    "Which product generated the highest revenue?",
    "Show monthly revenue trends.",
    "Which region has the highest revenue?",
    "Compare revenue between January 2026 and February 2026."
]

for example in examples:
    st.sidebar.caption(f"• {example}")


# --------------------------------------------------
# Main Interface
# --------------------------------------------------

st.title("📊 SalesIQ Business Intelligence")

st.caption(
    "Ask questions. Discover insights. Make better decisions."
)

st.divider()

st.subheader("🤖 Ask SalesIQ")

st.write(
    "Ask any question about your sales data. "
    "SalesIQ will analyze it and display the relevant results."
)

question = st.text_input(
    "Enter your business question",
    placeholder="e.g. Which product generated the highest revenue?",
    key="question_input"
)

if st.button("Ask SalesIQ", type="primary"):

    if not question.strip():
        st.warning("Please enter a question.")

    else:
        with st.spinner("Analyzing your question..."):

            answer = ask_question(question)

            if answer:
                st.session_state.answer = answer
            else:
                st.session_state.answer = None


# --------------------------------------------------
# Dynamic Answer Section
# --------------------------------------------------

if st.session_state.answer:

    st.divider()

    display_answer(st.session_state.answer)


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.divider()

st.caption(
    "SalesIQ | AI-Powered Business Intelligence Assistant"
)
