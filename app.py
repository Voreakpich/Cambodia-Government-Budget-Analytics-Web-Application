# CamBud — Cambodia Budget Analytics
# Built using the same straightforward structure and Streamlit approach
# as the EduRisk Lab 05 app.py supplied by the user.

from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="CamBud Analytics",
    page_icon=None,
    layout="wide"
)


# LOAD CSS
def load_css():
    """Load style.css from the same folder as app.py."""
    css_path = Path(__file__).resolve().parent / "style.css"

    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        st.warning(
            f"CSS file not found: {css_path.name}. "
            "Using Streamlit's default styling."
        )


load_css()


# 2. LOAD CAMBODIAN BUDGET DATA
@st.cache_data
def load_budget_data(file_path):
    """Read the translated MEF CSV file and cache it."""
    return pd.read_csv(file_path)


DATA_PATH = Path(__file__).resolve().parent / "budget_data.csv"

if not DATA_PATH.is_file():
    st.error(
        "budget_data.csv was not found. "
        "Please place it in the same folder as app.py."
    )
    st.stop()

try:
    budget_df = load_budget_data(str(DATA_PATH))
except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(
        "Could not read budget_data.csv. Please check the file format. "
        f"Details: {error}"
    )
    st.stop()


# 3. CHECK DATA AND PREPARE COLUMNS
required_columns = {
    "Fiscal Year",
    "Government Entity",
    "Budget Category",
    "Approved Budget (Million KHR)"
}
missing_columns = required_columns.difference(budget_df.columns)

if missing_columns:
    st.error(
        "Missing required column(s) in budget_data.csv: "
        + ", ".join(sorted(missing_columns))
    )
    st.stop()

budget_df["Fiscal Year"] = pd.to_numeric(
    budget_df["Fiscal Year"], errors="coerce"
)
budget_df["Approved Budget (Million KHR)"] = pd.to_numeric(
    budget_df["Approved Budget (Million KHR)"], errors="coerce"
)
budget_df["Government Entity"] = (
    budget_df["Government Entity"].astype("string").str.strip()
)
budget_df["Budget Category"] = (
    budget_df["Budget Category"].astype("string").str.strip()
)

if budget_df["Fiscal Year"].isna().any():
    st.error("Fiscal Year contains empty or non-numeric values.")
    st.stop()

if budget_df["Government Entity"].isna().any() or budget_df["Budget Category"].isna().any():
    st.error("Government Entity and Budget Category cannot be empty.")
    st.stop()

# Missing budget amounts from the original MEF file are intentionally retained.
# They are excluded from calculations instead of being replaced with zero.
valid_budget_df = budget_df.dropna(
    subset=["Approved Budget (Million KHR)"]
).copy()

if valid_budget_df.empty:
    st.error("There are no valid budget amounts available for analysis.")
    st.stop()


# 4. DATA SUMMARY AND HELPER FUNCTIONS
def format_budget(value):
    """Format budget values in million KHR."""
    return f"{value:,.2f}"


def prepare_chart(fig, height=350):
    """Apply consistent chart layout and Times New Roman font."""
    fig.update_layout(
        height=height,
        font=dict(
            family="Times New Roman",
            size=13,
            color="#183247"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=15, r=15, t=45, b=15),
        legend_title_text=""
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E4EEF5", zeroline=False)
    return fig


def styled_budget_table(dataframe):
    """Format budget amounts in tables without changing source values."""
    if "Approved Budget (Million KHR)" not in dataframe.columns:
        return dataframe

    return dataframe.style.format(
        {"Approved Budget (Million KHR)": "{:,.2f}"},
        na_rep="Not reported"
    )


# 5. SIDEBAR NAVIGATION
PAGE_LABELS = {
    "Home": "Home",
    "Dashboard": "Dashboard",
    "Budget Analysis": "Budget Analysis",
    "Entity Analysis": "Entity Analysis",
    "Data Explorer": "Data Explorer",
    "About": "About"
}

with st.sidebar:
    st.title("CamBud Menu")
    st.caption("Cambodia Budget Analytics")
    st.divider()

    selected_page = st.radio(
        "Select Page",
        list(PAGE_LABELS.keys()),
        format_func=lambda page: PAGE_LABELS[page]
    )

    st.divider()
    st.caption("DATA SOURCE")
    st.markdown(
        "[Ministry of Economy and Finance (MEF)]"
        "(https://data.mef.gov.kh/datasets/pd_69942a5e9eaed400071a6ca9)"
    )
    st.caption("Approved Budget Law · FY2021–FY2026")


# 6. COMMON DASHBOARD FILTERS
available_years = sorted(
    valid_budget_df["Fiscal Year"].astype(int).unique().tolist()
)
available_entities = sorted(
    valid_budget_df["Government Entity"].dropna().unique().tolist()
)
available_categories = sorted(
    valid_budget_df["Budget Category"].dropna().unique().tolist()
)

st.title("CamBud | Cambodia Budget Analytics")
st.caption(
    "Explore approved government budget allocations by fiscal year, "
    "expenditure category, and government entity."
)

with st.expander("Dashboard Filters", expanded=True):
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        selected_years = st.multiselect(
            "Filter by Fiscal Year",
            available_years,
            default=available_years
        )

    with filter_col2:
        selected_categories = st.multiselect(
            "Filter by Budget Category",
            available_categories,
            default=available_categories
        )

    with filter_col3:
        selected_entities = st.multiselect(
            "Filter by Government Entity",
            available_entities,
            default=available_entities
        )

filtered_df = valid_budget_df[
    valid_budget_df["Fiscal Year"].isin(selected_years)
    & valid_budget_df["Budget Category"].isin(selected_categories)
    & valid_budget_df["Government Entity"].isin(selected_entities)
].copy()

if filtered_df.empty:
    st.warning(
        "No budget records match the selected filters. "
        "Please adjust your selections."
    )
    st.stop()

# Missing-value count is shown separately to avoid hiding source data limitations.
filtered_source_rows = budget_df[
    budget_df["Fiscal Year"].isin(selected_years)
    & budget_df["Budget Category"].isin(selected_categories)
    & budget_df["Government Entity"].isin(selected_entities)
].copy()
missing_amount_count = int(
    filtered_source_rows["Approved Budget (Million KHR)"].isna().sum()
)

total_budget = filtered_df["Approved Budget (Million KHR)"].sum()
current_budget = filtered_df.loc[
    filtered_df["Budget Category"] == "Current Expenditure",
    "Approved Budget (Million KHR)"
].sum()
capital_budget = filtered_df.loc[
    filtered_df["Budget Category"] == "Capital Expenditure",
    "Approved Budget (Million KHR)"
].sum()
total_entities = filtered_df["Government Entity"].nunique()


# 7. HOME PAGE
if selected_page == "Home":
    st.title("Welcome to CamBud")
    st.subheader("Cambodia Government Budget Analytics")

    st.write(
        "CamBud is an interactive web application for exploring Cambodia's "
        "approved government budget allocations. It helps users understand "
        "how budget allocations are distributed across fiscal years, "
        "expenditure categories, and government entities."
    )

    st.success("CamBud is running successfully!")

    st.subheader("Project Overview")
    overview_col1, overview_col2 = st.columns(2)

    with overview_col1:
        st.markdown("**Main Features**")
        st.write(
            "- Dashboard overview and key budget indicators\n"
            "- Current and capital expenditure analysis\n"
            "- Government entity ranking\n"
            "- Searchable data table and CSV export"
        )

    with overview_col2:
        st.markdown("**Dataset Information**")
        st.write(
            "- Publisher: Ministry of Economy and Finance (MEF)\n"
            "- Fiscal years: 2021–2026\n"
            "- Currency: Cambodian Riel (KHR)\n"
            "- Unit: Million KHR"
        )

    st.info(
        "CamBud analyzes approved Budget Law allocations. "
        "These figures should not be interpreted as actual cash expenditure "
        "or budget execution."
    )


# 8. DASHBOARD PAGE
elif selected_page == "Dashboard":
    st.title("Government Budget Dashboard")

    st.write(
        "Use the filters above to explore approved budget allocations "
        "by fiscal year, category, and government entity."
    )

    st.subheader("Budget Overview")

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric(
            "Total Approved Budget",
            f"{format_budget(total_budget)}",
            "Million KHR"
        )

    with metric_col2:
        st.metric(
            "Current Expenditure",
            f"{format_budget(current_budget)}",
            "Million KHR"
        )

    with metric_col3:
        st.metric(
            "Capital Expenditure",
            f"{format_budget(capital_budget)}",
            "Million KHR"
        )

    with metric_col4:
        st.metric(
            "Government Entities",
            total_entities
        )

    if missing_amount_count > 0:
        st.warning(
            f"The selected source records contain {missing_amount_count} "
            "blank budget amount(s). They are excluded from calculations "
            "and have not been estimated."
        )

    # Budget trend and category distribution
    st.subheader("Budget Visualization")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.write("Approved Budget by Fiscal Year")

        yearly_budget = (
            filtered_df.groupby("Fiscal Year", as_index=False)
            ["Approved Budget (Million KHR)"].sum()
        )

        fig_yearly = px.line(
            yearly_budget,
            x="Fiscal Year",
            y="Approved Budget (Million KHR)",
            markers=True,
            title="Approved Budget Trend",
            color_discrete_sequence=["#176B9A"]
        )
        fig_yearly.update_traces(
            line=dict(width=3),
            marker=dict(size=9, color="#38BDF8")
        )
        st.plotly_chart(
            prepare_chart(fig_yearly),
            use_container_width=True
        )

    with chart_col2:
        st.write("Budget by Expenditure Category")

        category_summary = (
            filtered_df.groupby("Budget Category", as_index=False)
            ["Approved Budget (Million KHR)"].sum()
        )

        fig_category = px.pie(
            category_summary,
            names="Budget Category",
            values="Approved Budget (Million KHR)",
            hole=0.5,
            title="Current vs Capital Expenditure",
            color="Budget Category",
            color_discrete_map={
                "Current Expenditure": "#176B9A",
                "Capital Expenditure": "#F59E0B"
            }
        )
        st.plotly_chart(
            prepare_chart(fig_category),
            use_container_width=True
        )

    # Largest government entity allocations
    st.subheader("Top Government Entities by Approved Budget")

    entity_summary = (
        filtered_df.groupby("Government Entity", as_index=False)
        ["Approved Budget (Million KHR)"].sum()
        .nlargest(10, "Approved Budget (Million KHR)")
        .sort_values("Approved Budget (Million KHR)")
    )

    fig_entities = px.bar(
        entity_summary,
        x="Approved Budget (Million KHR)",
        y="Government Entity",
        orientation="h",
        title="Top 10 Government Entities",
        color="Approved Budget (Million KHR)",
        color_continuous_scale=["#BAE6FD", "#176B9A", "#0B2942"]
    )
    fig_entities.update_layout(coloraxis_showscale=False)
    st.plotly_chart(
        prepare_chart(fig_entities, height=430),
        use_container_width=True
    )


# 9. BUDGET ANALYSIS PAGE
elif selected_page == "Budget Analysis":
    st.title("Budget Analysis")

    st.write(
        "Compare approved current and capital expenditure allocations "
        "across the selected fiscal years."
    )

    st.subheader("Current vs Capital Expenditure")

    yearly_category = (
        filtered_df.groupby(
            ["Fiscal Year", "Budget Category"], as_index=False
        )["Approved Budget (Million KHR)"].sum()
    )

    fig_comparison = px.bar(
        yearly_category,
        x="Fiscal Year",
        y="Approved Budget (Million KHR)",
        color="Budget Category",
        barmode="group",
        title="Budget Allocation by Year and Category",
        color_discrete_map={
            "Current Expenditure": "#176B9A",
            "Capital Expenditure": "#F59E0B"
        }
    )

    st.plotly_chart(
        prepare_chart(fig_comparison, height=430),
        use_container_width=True
    )

    st.subheader("Budget Category Summary")

    category_summary = (
        filtered_df.groupby("Budget Category", as_index=False)
        ["Approved Budget (Million KHR)"].sum()
        .sort_values("Approved Budget (Million KHR)", ascending=False)
    )

    category_total = category_summary["Approved Budget (Million KHR)"].sum()
    if category_total > 0:
        category_summary["Share (%)"] = (
            category_summary["Approved Budget (Million KHR)"]
            / category_total * 100
        ).round(2)

    st.dataframe(
        styled_budget_table(category_summary),
        use_container_width=True,
        hide_index=True
    )


# 10. ENTITY ANALYSIS PAGE
elif selected_page == "Entity Analysis":
    st.title("Government Entity Analysis")

    st.write(
        "Explore and rank government entities according to their "
        "approved budget allocations."
    )

    entity_ranking = (
        filtered_df.groupby("Government Entity", as_index=False)
        ["Approved Budget (Million KHR)"].sum()
        .sort_values("Approved Budget (Million KHR)", ascending=False)
    )

    maximum_entities = max(5, min(30, len(entity_ranking)))
    selected_top_n = st.slider(
        "Number of Entities to Display",
        min_value=5,
        max_value=maximum_entities,
        value=min(10, maximum_entities)
    )

    displayed_entities = (
        entity_ranking.head(selected_top_n)
        .sort_values("Approved Budget (Million KHR)")
    )

    fig_ranking = px.bar(
        displayed_entities,
        x="Approved Budget (Million KHR)",
        y="Government Entity",
        orientation="h",
        title=f"Top {selected_top_n} Government Entities",
        color="Approved Budget (Million KHR)",
        color_continuous_scale=["#BAE6FD", "#176B9A", "#0B2942"]
    )
    fig_ranking.update_layout(coloraxis_showscale=False)

    st.plotly_chart(
        prepare_chart(fig_ranking, height=max(400, selected_top_n * 35)),
        use_container_width=True
    )

    st.subheader("Government Entity Ranking Table")

    entity_ranking.insert(
        0, "Rank", range(1, len(entity_ranking) + 1)
    )

    st.dataframe(
        styled_budget_table(entity_ranking),
        use_container_width=True,
        hide_index=True
    )


# 11. DATA EXPLORER PAGE
elif selected_page == "Data Explorer":
    st.title("Budget Data Explorer")

    st.write(
        "Search, inspect, and download records from the translated "
        "Cambodian government budget dataset."
    )

    search_entity = st.text_input(
        "Search Government Entity",
        placeholder="Enter a ministry or government entity name..."
    )

    selected_data = filtered_df.copy()

    if search_entity.strip():
        selected_data = selected_data[
            selected_data["Government Entity"].str.contains(
                search_entity.strip(),
                case=False,
                na=False
            )
        ]

    st.subheader("Dataset Information")
    st.write("Rows and columns:", budget_df.shape)
    st.write("Column names:", budget_df.columns.tolist())

    st.subheader("Filtered Budget Records")
    st.caption(f"{len(selected_data):,} records displayed")

    st.dataframe(
        styled_budget_table(selected_data),
        use_container_width=True,
        hide_index=True
    )

    csv_data = selected_data.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "Download Filtered Budget Data",
        data=csv_data,
        file_name="CamBud_Filtered_Budget_Data.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.info(
        "Blank budget amounts in the original source are displayed as "
        "'Not reported' in formatted tables."
    )


# 12. ABOUT PAGE
elif selected_page == "About":
    st.title("About CamBud")

    st.write("Project Name: CamBud")
    st.write("Project Title: Cambodia Budget Analytics")
    st.write("Course: Web Application Development")
    st.write("Framework: Python and Streamlit")
    st.write("Styling: CSS")
    st.write("Data Publisher: Ministry of Economy and Finance (MEF), Cambodia")

    st.subheader("Project Purpose")
    st.write(
        "CamBud provides an accessible way to explore approved government "
        "budget allocations across fiscal years, expenditure categories, "
        "and government entities."
    )

    st.subheader("Data Source")
    st.markdown(
        "[Current and Capital Expenditure by Entity of Budget Law "
        "in Brief FY2021–FY2026]"
        "(https://data.mef.gov.kh/datasets/pd_69942a5e9eaed400071a6ca9)"
    )

    st.warning(
        "Important: This dataset represents approved Budget Law allocations. "
        "It does not, by itself, show actual expenditure, budget execution, "
        "or remaining budget."
    )

# 13. FOOTER
st.divider()
st.caption(
    "CamBud | Cambodia Budget Analytics · Source: Ministry of Economy and "
    "Finance (MEF), Cambodia · Amounts are expressed in million KHR."
)
