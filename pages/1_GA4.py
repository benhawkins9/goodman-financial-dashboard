import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import json

st.set_page_config(
    page_title="GA4 — Goodman Financial",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
[data-testid="stSidebar"]{background-color:#0F6E56;}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span{color:rgba(255,255,255,0.92)!important;}
[data-testid="stSidebarNav"] a[aria-selected="true"]{background-color:rgba(255,255,255,0.18)!important;border-left:3px solid white;}
.stButton>button[kind="primary"]{background-color:#0F6E56!important;border-color:#0F6E56!important;color:white!important;font-weight:600;border-radius:6px;}
[data-testid="stMetricValue"]{color:#0F6E56!important;font-weight:700!important;}
h1,h2{color:#0F6E56!important;font-weight:700;}
hr{border-color:#E0EDE9!important;}
</style>
""", unsafe_allow_html=True)

# ── Auth guard ───────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

# ── Helpers ──────────────────────────────────────────────────────────────────
COLORS = ["#0F6E56", "#1A9E7A", "#2DB896", "#5DCFB2", "#88E5CD", "#B4F0E0"]

def kpi_card(title, value, delta=None):
    delta_html = ""
    if delta is not None:
        clr = "#1B8E4B" if delta >= 0 else "#C0392B"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<p style="color:{clr};font-size:0.82rem;margin:4px 0 0;">{arrow} {abs(delta):.1f}%</p>'
    return f"""<div style="background:#F4FBF8;border:1px solid #D4EDE5;border-left:4px solid #0F6E56;
                border-radius:8px;padding:1.1rem 1.25rem;">
        <p style="color:#6B7280;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 6px;">{title}</p>
        <h2 style="color:#0F2A22;font-size:1.7rem;font-weight:700;margin:0;">{value}</h2>
        {delta_html}</div>"""

def chart_layout(title="", xaxis_title="", yaxis_title=""):
    return dict(
        title=dict(text=title, font=dict(size=15, color="#0F2A22"), x=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", color="#374151"),
        xaxis=dict(title=xaxis_title, gridcolor="#F3F4F6", linecolor="#E5E7EB", showgrid=True),
        yaxis=dict(title=yaxis_title, gridcolor="#F3F4F6", linecolor="#E5E7EB", showgrid=True),
        margin=dict(t=50, b=40, l=50, r=20),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Goodman Financial")
    st.markdown("---")
    st.markdown("**Date Range**")
    range_opt = st.selectbox("Range", ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"], index=1, label_visibility="collapsed")
    today = datetime.today().date()
    if range_opt == "Last 7 days":
        start_date, end_date = today - timedelta(days=7), today
    elif range_opt == "Last 30 days":
        start_date, end_date = today - timedelta(days=30), today
    elif range_opt == "Last 90 days":
        start_date, end_date = today - timedelta(days=90), today
    else:
        start_date = st.date_input("Start", value=today - timedelta(days=30))
        end_date = st.date_input("End", value=today)
    st.caption(f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}")
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()


# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ga4(start: str, end: str, property_id: str):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric, OrderBy
    )
    from google.oauth2 import service_account

    creds_info = json.loads(st.secrets["GA4_CREDENTIALS"])
    credentials = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=credentials)

    # ── Summary totals ──
    summary_req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
    )
    summary_resp = client.run_report(summary_req)
    row = summary_resp.rows[0].metric_values if summary_resp.rows else [None]*5

    # ── Daily sessions + users ──
    daily_req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
    )
    daily_resp = client.run_report(daily_req)
    daily_rows = [
        {
            "date": r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value),
            "users": int(r.metric_values[1].value),
        }
        for r in daily_resp.rows
    ]

    # ── Top pages ──
    pages_req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews"), Metric(name="sessions"), Metric(name="averageSessionDuration")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=10,
    )
    pages_resp = client.run_report(pages_req)
    pages_rows = [
        {
            "page": r.dimension_values[0].value,
            "views": int(r.metric_values[0].value),
            "sessions": int(r.metric_values[1].value),
            "avg_duration": float(r.metric_values[2].value),
        }
        for r in pages_resp.rows
    ]

    # ── Traffic sources ──
    sources_req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=10,
    )
    sources_resp = client.run_report(sources_req)
    sources_rows = [
        {
            "channel": r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value),
        }
        for r in sources_resp.rows
    ]

    return {
        "sessions": int(row[0].value) if row[0] else 0,
        "users": int(row[1].value) if row[1] else 0,
        "pageviews": int(row[2].value) if row[2] else 0,
        "bounce_rate": float(row[3].value) * 100 if row[3] else 0,
        "avg_duration": float(row[4].value) if row[4] else 0,
        "daily": daily_rows,
        "pages": pages_rows,
        "sources": sources_rows,
    }


# ── Page ─────────────────────────────────────────────────────────────────────
st.markdown("## Google Analytics 4")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

try:
    property_id = st.secrets["GA4_PROPERTY_ID"]
except KeyError:
    st.error("GA4_PROPERTY_ID is missing from secrets.toml")
    st.stop()

with st.spinner("Fetching GA4 data…"):
    try:
        data = fetch_ga4(start_str, end_str, str(property_id))
    except Exception as e:
        st.error(f"Could not load GA4 data: {e}")
        st.stop()

# ── KPI Cards ──
def fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(kpi_card("Sessions", f"{data['sessions']:,}"), unsafe_allow_html=True)
c2.markdown(kpi_card("Active Users", f"{data['users']:,}"), unsafe_allow_html=True)
c3.markdown(kpi_card("Page Views", f"{data['pageviews']:,}"), unsafe_allow_html=True)
c4.markdown(kpi_card("Bounce Rate", f"{data['bounce_rate']:.1f}%"), unsafe_allow_html=True)
c5.markdown(kpi_card("Avg Session", fmt_duration(data["avg_duration"])), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Daily line chart ──
daily_df = pd.DataFrame(data["daily"])
if not daily_df.empty:
    daily_df["date"] = pd.to_datetime(daily_df["date"], format="%Y%m%d")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_df["date"], y=daily_df["sessions"],
        name="Sessions", line=dict(color="#0F6E56", width=2.5),
        fill="tozeroy", fillcolor="rgba(15,110,86,0.08)",
    ))
    fig.add_trace(go.Scatter(
        x=daily_df["date"], y=daily_df["users"],
        name="Active Users", line=dict(color="#1A9E7A", width=2, dash="dot"),
    ))
    fig.update_layout(**chart_layout("Sessions & Active Users Over Time", "Date", "Count"))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
col_left, col_right = st.columns(2)

# ── Top pages bar chart ──
pages_df = pd.DataFrame(data["pages"])
if not pages_df.empty:
    with col_left:
        fig2 = go.Figure(go.Bar(
            x=pages_df["views"],
            y=pages_df["page"].str[:40],
            orientation="h",
            marker_color=COLORS[0],
            text=pages_df["views"].apply(lambda v: f"{v:,}"),
            textposition="outside",
        ))
        fig2.update_layout(**chart_layout("Top 10 Pages by Views"))
        fig2.update_layout(yaxis=dict(autorange="reversed"), height=420)
        st.plotly_chart(fig2, use_container_width=True)

# ── Traffic channels donut ──
sources_df = pd.DataFrame(data["sources"])
if not sources_df.empty:
    with col_right:
        fig3 = px.pie(
            sources_df, values="sessions", names="channel",
            hole=0.52, color_discrete_sequence=COLORS,
        )
        fig3.update_layout(
            **chart_layout("Sessions by Channel"),
            showlegend=True,
        )
        fig3.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value:,} sessions")
        st.plotly_chart(fig3, use_container_width=True)

# ── Data table ──
st.markdown("#### Top Pages — Detail")
if not pages_df.empty:
    display_df = pages_df.rename(columns={
        "page": "Page Path",
        "views": "Page Views",
        "sessions": "Sessions",
        "avg_duration": "Avg Duration (s)",
    })
    display_df["Avg Duration (s)"] = display_df["Avg Duration (s)"].apply(lambda x: f"{x:.1f}s")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(f"Data source: Google Analytics 4 · Property {property_id} · Refreshed hourly")
