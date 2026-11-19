import streamlit as st
import pandas as pd
import altair as alt

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cambodia National Budget Analytics",
    page_icon="🇰🇭",
    layout="wide",
    initial_sidebar_state="expanded",
)

KHR_PER_USD = 4100.0  # Approx KHR to USD conversion rate

# ── Custom Styling ────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 5px solid #1f77b4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("budget_data.csv")
    df["Approved Budget (Million KHR)"] = pd.to_numeric(
        df["Approved Budget (Million KHR)"], errors="coerce"
    ).fillna(0)
    # Standardize slight entity name variations if any
    df["Government Entity"] = df["Government Entity"].str.strip()
    return df

df_raw = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🇰🇭 CamBud Analytics")
st.sidebar.caption("Cambodia National Budget (2021–2026)")
st.sidebar.divider()

# Currency toggle
currency = st.sidebar.radio(
    "💵 Currency Display",
    ["Million KHR", "Million USD"],
    horizontal=True,
)
multiplier = 1.0 if currency == "Million KHR" else (1.0 / KHR_PER_USD)
unit_label = "M KHR" if currency == "Million KHR" else "M USD"

df = df_raw.copy()
df["Budget"] = df["Approved Budget (Million KHR)"] * multiplier

st.sidebar.divider()
st.sidebar.subheader("Filters")

# Year multi-select
available_years = sorted(df["Fiscal Year"].unique())
selected_years = st.sidebar.multiselect(
    "Fiscal Years",
    available_years,
    default=available_years,
)

# Budget category filter
categories = sorted(df["Budget Category"].unique())
selected_cats = st.sidebar.multiselect(
    "Budget Category",
    categories,
    default=categories,
)

# Entity multi-select
all_entities = sorted(df["Government Entity"].unique())
selected_entities = st.sidebar.multiselect(
    "Filter Specific Entities (leave empty for all)",
    all_entities,
    default=[],
)

# Apply filters
mask = df["Fiscal Year"].isin(selected_years) & df["Budget Category"].isin(selected_cats)
if selected_entities:
    mask &= df["Government Entity"].isin(selected_entities)

filtered = df[mask].copy()

# Guard against empty selection
if filtered.empty:
    st.warning("⚠️ No data matches your filter selection. Please adjust sidebar filters.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_overview, tab_comparison, tab_deepdive, tab_data = st.tabs([
    "📊 Overview & Macro Trends",
    "🏛️ Ministry Rankings & YoY",
    "🔍 Ministry Deep Dive",
    "📄 Data Explorer",
])

# ==============================================================================
# TAB 1: OVERVIEW & MACRO TRENDS
# ==============================================================================
with tab_overview:
    st.title("🇰🇭 Cambodia National Budget Overview")
    st.caption(f"Displaying approved figures in **{unit_label}** | Fiscal Years: {', '.join(map(str, selected_years))}")

    # Top KPI Metrics
    total_val = filtered["Budget"].sum()
    capital_val = filtered[filtered["Budget Category"] == "Capital Expenditure"]["Budget"].sum()
    current_val = filtered[filtered["Budget Category"] == "Current Expenditure"]["Budget"].sum()
    entity_count = filtered["Government Entity"].nunique()

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("💰 Total Budget", f"{total_val:,.1f} {unit_label}")
    kpi2.metric(
        "🏗️ Capital Expenditure",
        f"{capital_val:,.1f} {unit_label}",
        f"{capital_val / total_val * 100:.1f}% of total" if total_val > 0 else "0%",
    )
    kpi3.metric(
        "📋 Current Expenditure",
        f"{current_val:,.1f} {unit_label}",
        f"{current_val / total_val * 100:.1f}% of total" if total_val > 0 else "0%",
    )
    kpi4.metric("🏛️ Active Entities", entity_count)

    st.divider()

    # Budget Trajectory over Years
    st.subheader("📈 National Budget Growth Trajectory (2021–2026)")
    trend_data = (
        filtered.groupby(["Fiscal Year", "Budget Category"])["Budget"]
        .sum()
        .reset_index()
    )

    trend_chart = (
        alt.Chart(trend_data)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("Fiscal Year:O", title="Fiscal Year"),
            y=alt.Y("Budget:Q", title=f"Budget ({unit_label})"),
            color=alt.Color("Budget Category:N", scale=alt.Scale(scheme="category10")),
            tooltip=[
                alt.Tooltip("Fiscal Year:O"),
                alt.Tooltip("Budget Category:N"),
                alt.Tooltip("Budget:Q", format=",.1f", title=f"Budget ({unit_label})"),
            ],
        )
        .properties(height=340)
        .interactive()
    )
    st.altair_chart(trend_chart, use_container_width=True)

    # Stacked Bar Composition & Donut
    c_left, c_right = st.columns([3, 2])
    with c_left:
        st.subheader("📊 Annual Capital vs. Current Proportion")
        stacked = (
            alt.Chart(trend_data)
            .mark_bar()
            .encode(
                x=alt.X("Fiscal Year:O", title="Fiscal Year"),
                y=alt.Y("Budget:Q", title=f"Budget ({unit_label})", stack="zero"),
                color=alt.Color("Budget Category:N"),
                tooltip=[
                    alt.Tooltip("Fiscal Year:O"),
                    alt.Tooltip("Budget Category:N"),
                    alt.Tooltip("Budget:Q", format=",.1f"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(stacked, use_container_width=True)

    with c_right:
        st.subheader("🍩 Overall Spending Allocation")
        cat_pie = (
            filtered.groupby("Budget Category")["Budget"]
            .sum()
            .reset_index()
        )
        donut = (
            alt.Chart(cat_pie)
            .mark_arc(innerRadius=70)
            .encode(
                theta=alt.Theta("Budget:Q"),
                color=alt.Color("Budget Category:N"),
                tooltip=[
                    alt.Tooltip("Budget Category:N"),
                    alt.Tooltip("Budget:Q", format=",.1f", title=f"Amount ({unit_label})"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(donut, use_container_width=True)

# ==============================================================================
# TAB 2: MINISTRY COMPARISONS & YOY
# ==============================================================================
with tab_comparison:
    st.title("🏛️ Ministry Allocations & Year-over-Year Dynamics")

    # Top Entities Horizontal Bar Chart
    top_limit = st.slider("Select number of top ministries to display:", 5, 30, 15)

    entity_totals = (
        filtered.groupby("Government Entity")["Budget"]
        .sum()
        .reset_index()
        .sort_values("Budget", ascending=False)
        .head(top_limit)
    )

    bar_chart = (
        alt.Chart(entity_totals)
        .mark_bar()
        .encode(
            x=alt.X("Budget:Q", title=f"Total Budget ({unit_label})"),
            y=alt.Y("Government Entity:N", sort="-x", title=""),
            color=alt.Color("Budget:Q", scale=alt.Scale(scheme="tealblues"), legend=None),
            tooltip=[
                alt.Tooltip("Government Entity:N"),
                alt.Tooltip("Budget:Q", format=",.1f", title=f"Budget ({unit_label})"),
            ],
        )
        .properties(height=max(350, top_limit * 22))
        .interactive()
    )
    st.altair_chart(bar_chart, use_container_width=True)

    st.divider()

    # Year-over-Year Growth Calculation
    st.subheader("📊 Year-over-Year (YoY) Change Analysis")
    col_y1, col_y2 = st.columns(2)
    y_from = col_y1.selectbox("Base Year", available_years, index=0)
    valid_to_years = [y for y in available_years if y > y_from]
    if not valid_to_years:
        valid_to_years = [available_years[-1]]
    y_to = col_y2.selectbox("Comparison Year", valid_to_years, index=len(valid_to_years) - 1)

    # Pivot table for comparison
    pivot_df = (
        df.groupby(["Government Entity", "Fiscal Year"])["Budget"]
        .sum()
        .unstack(fill_value=0)
    )

    if y_from in pivot_df.columns and y_to in pivot_df.columns:
        yoy_df = pd.DataFrame({
            "Base Budget": pivot_df[y_from],
            "Comp Budget": pivot_df[y_to],
        })
        yoy_df["Diff"] = yoy_df["Comp Budget"] - yoy_df["Base Budget"]
        yoy_df["YoY Growth %"] = (
            (yoy_df["Diff"] / yoy_df["Base Budget"].replace(0, pd.NA)) * 100
        ).fillna(0)
        yoy_df = yoy_df.reset_index()

        col_gain, col_decline = st.columns(2)

        with col_gain:
            st.markdown(f"##### 🚀 Top 5 Growth Ministries ({y_from} → {y_to})")
            top_gainers = yoy_df[yoy_df["Base Budget"] > 0].sort_values("YoY Growth %", ascending=False).head(5)
            st.dataframe(
                top_gainers[["Government Entity", "Base Budget", "Comp Budget", "YoY Growth %"]].style.format({
                    "Base Budget": "{:,.1f}",
                    "Comp Budget": "{:,.1f}",
                    "YoY Growth %": "+{:,.1f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )

        with col_decline:
            st.markdown(f"##### 🔻 Top 5 Decliners / Cut Budgets ({y_from} → {y_to})")
            top_cut = yoy_df[yoy_df["Base Budget"] > 0].sort_values("YoY Growth %", ascending=True).head(5)
            st.dataframe(
                top_cut[["Government Entity", "Base Budget", "Comp Budget", "YoY Growth %"]].style.format({
                    "Base Budget": "{:,.1f}",
                    "Comp Budget": "{:,.1f}",
                    "YoY Growth %": "{:,.1f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )

    st.divider()

    # Heatmap
    st.subheader("🗺️ Budget Allocation Heatmap Across All Years")
    heat_data = (
        filtered.groupby(["Government Entity", "Fiscal Year"])["Budget"]
        .sum()
        .reset_index()
    )
    heat = (
        alt.Chart(heat_data)
        .mark_rect()
        .encode(
            x=alt.X("Fiscal Year:O", title="Fiscal Year"),
            y=alt.Y("Government Entity:N", sort="-x", title=""),
            color=alt.Color(
                "Budget:Q",
                scale=alt.Scale(scheme="purples"),
                title=f"{unit_label}",
            ),
            tooltip=[
                alt.Tooltip("Government Entity:N"),
                alt.Tooltip("Fiscal Year:O"),
                alt.Tooltip("Budget:Q", format=",.1f", title=f"Budget ({unit_label})"),
            ],
        )
        .properties(height=max(380, filtered["Government Entity"].nunique() * 18))
        .interactive()
    )
    st.altair_chart(heat, use_container_width=True)

# ==============================================================================
# TAB 3: MINISTRY DEEP DIVE
# ==============================================================================
with tab_deepdive:
    st.title("🔍 Ministry Deep Dive")
    st.caption("Inspect 6-year historical breakdown and capital vs. current expenditure ratio for any specific institution.")

    picked_entity = st.selectbox(
        "Select a Government Entity to Analyze:",
        all_entities,
        index=all_entities.index("Ministry of Education, Youth and Sport")
        if "Ministry of Education, Youth and Sport" in all_entities else 0,
    )

    entity_data = df[df["Government Entity"] == picked_entity].copy()

    # Entity KPIs
    total_ent = entity_data["Budget"].sum()
    avg_annual = entity_data.groupby("Fiscal Year")["Budget"].sum().mean()
    cap_ent = entity_data[entity_data["Budget Category"] == "Capital Expenditure"]["Budget"].sum()
    cur_ent = entity_data[entity_data["Budget Category"] == "Current Expenditure"]["Budget"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cumulative 6-Yr Budget", f"{total_ent:,.1f} {unit_label}")
    m2.metric("Average Annual Budget", f"{avg_annual:,.1f} {unit_label}")
    m3.metric(
        "Total Capital Expenditure",
        f"{cap_ent:,.1f} {unit_label}",
        f"{cap_ent / total_ent * 100:.1f}%" if total_ent > 0 else "0%",
    )
    m4.metric(
        "Total Current Expenditure",
        f"{cur_ent:,.1f} {unit_label}",
        f"{cur_ent / total_ent * 100:.1f}%" if total_ent > 0 else "0%",
    )

    st.divider()

    # Historical Breakup Line & Stacked
    d_col1, d_col2 = st.columns(2)

    with d_col1:
        st.subheader("📈 Annual Trajectory by Category")
        d_line = (
            alt.Chart(entity_data)
            .mark_line(point=True, strokeWidth=2.5)
            .encode(
                x=alt.X("Fiscal Year:O", title="Fiscal Year"),
                y=alt.Y("Budget:Q", title=f"Budget ({unit_label})"),
                color=alt.Color("Budget Category:N"),
                tooltip=[
                    alt.Tooltip("Fiscal Year:O"),
                    alt.Tooltip("Budget Category:N"),
                    alt.Tooltip("Budget:Q", format=",.1f"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(d_line, use_container_width=True)

    with d_col2:
        st.subheader("📊 Capital vs. Current Breakdown")
        d_bar = (
            alt.Chart(entity_data)
            .mark_bar()
            .encode(
                x=alt.X("Fiscal Year:O", title="Fiscal Year"),
                y=alt.Y("Budget:Q", title=f"Budget ({unit_label})"),
                color=alt.Color("Budget Category:N"),
                tooltip=[
                    alt.Tooltip("Fiscal Year:O"),
                    alt.Tooltip("Budget Category:N"),
                    alt.Tooltip("Budget:Q", format=",.1f"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(d_bar, use_container_width=True)

    # Detailed Table for this Entity
    st.subheader(f"📋 Raw Figures for {picked_entity}")
    entity_pivot = (
        entity_data.pivot_table(
            index="Budget Category",
            columns="Fiscal Year",
            values="Budget",
            aggfunc="sum",
            fill_value=0,
        )
    )
    entity_pivot["Total"] = entity_pivot.sum(axis=1)
    st.dataframe(
        entity_pivot.style.format("{:,.1f}"),
        use_container_width=True,
    )

# ==============================================================================
# TAB 4: DATA EXPLORER & EXPORT
# ==============================================================================
with tab_data:
    st.title("📄 Data Explorer & Export")
    st.caption("Search, sort, filter, and export the dataset.")

    search_query = st.text_input("🔍 Search entity name:", "")
    view_df = filtered.copy()
    if search_query:
        view_df = view_df[view_df["Government Entity"].str.contains(search_query, case=False, na=False)]

    st.dataframe(
        view_df[["Fiscal Year", "Government Entity", "Budget Category", "Budget"]]
        .sort_values(["Fiscal Year", "Government Entity"])
        .reset_index(drop=True)
        .style.format({"Budget": "{:,.1f}"}),
        use_container_width=True,
        height=450,
    )

    csv_data = view_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"⬇️ Download Current View as CSV ({len(view_df)} rows)",
        data=csv_data,
        file_name="cambodia_budget_export.csv",
        mime="text/csv",
    )

