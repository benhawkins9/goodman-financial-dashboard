import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="GA4 — Goodman Financial", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main,.block-container{background-color:#0F1A14!important;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] span{color:#E8F5E9!important;}
.stCaption,[data-testid="stCaptionContainer"]{color:#9AC89E!important;}
label{color:#9AC89E!important;}
h1{color:#E8F5E9!important;font-weight:700;}h2{color:#E8F5E9!important;font-weight:600;}h3,h4{color:#9AC89E!important;font-weight:600;}
[data-testid="stSidebar"]{background-color:#0F6E56!important;}
[data-testid="stSidebar"] *{color:rgba(255,255,255,0.92)!important;}
[data-testid="stSidebarNav"] a[aria-selected="true"]{background-color:rgba(255,255,255,0.18)!important;border-left:3px solid white;}
.stButton>button[kind="primary"]{background-color:#4CAF50!important;border-color:#4CAF50!important;color:#0F1A14!important;font-weight:700;border-radius:6px;}
.stButton>button:not([kind="primary"]){background-color:#1A2E22!important;border-color:#2A4A35!important;color:#E8F5E9!important;border-radius:6px;}
.stTabs [data-baseweb="tab-list"]{background-color:transparent;border-bottom:2px solid #2A4A35;}
.stTabs [data-baseweb="tab"]{color:#9AC89E!important;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{border-bottom:3px solid #4CAF50!important;color:#E8F5E9!important;font-weight:600;}
[data-testid="stDataFrame"]{border:1px solid #2A4A35;border-radius:8px;}
[data-testid="stAlert"]{background-color:#1A2E22!important;border-color:#2A4A35!important;}
hr{border-color:#2A4A35!important;}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

COLORS = ["#4CAF50", "#2DB896", "#66BB6A", "#81C784", "#1A9E7A", "#0F6E56"]

def kpi_card(title, value, delta=None):
    delta_html = ""
    if delta is not None:
        clr = "#4CAF50" if delta >= 0 else "#EF5350"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<p style="color:{clr};font-size:0.82rem;margin:4px 0 0;">{arrow} {abs(delta):.1f}%</p>'
    return f"""<div style="background:#1A2E22;border:1px solid #2A4A35;border-left:4px solid #4CAF50;
                border-radius:8px;padding:1.1rem 1.25rem;">
        <p style="color:#9AC89E;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 6px;">{title}</p>
        <h2 style="color:#4CAF50;font-size:1.7rem;font-weight:700;margin:0;">{value}</h2>
        {delta_html}</div>"""

def chart_layout(title="", xaxis_title="", yaxis_title=""):
    return dict(
        title=dict(text=title, font=dict(size=15, color="#E8F5E9"), x=0),
        plot_bgcolor="#0F1A14", paper_bgcolor="#0F1A14",
        font=dict(family="Inter, sans-serif", color="#E8F5E9"),
        xaxis=dict(title=xaxis_title, gridcolor="#1A2E22", linecolor="#2A4A35",
                   color="#9AC89E", tickfont=dict(color="#9AC89E"), title_font=dict(color="#9AC89E")),
        yaxis=dict(title=yaxis_title, gridcolor="#1A2E22", linecolor="#2A4A35",
                   color="#9AC89E", tickfont=dict(color="#9AC89E"), title_font=dict(color="#9AC89E")),
        margin=dict(t=50, b=40, l=50, r=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#E8F5E9")),
        hovermode="x unified",
    )

with st.sidebar:
    st.markdown("### 📊 Goodman Financial")
    st.markdown("---")
    st.markdown("**Date Range**")
    range_opt = st.selectbox("Range", ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
                             index=1, label_visibility="collapsed")
    today = datetime.today().date()
    if range_opt == "Last 7 days":     start_date, end_date = today - timedelta(days=7), today
    elif range_opt == "Last 30 days":  start_date, end_date = today - timedelta(days=30), today
    elif range_opt == "Last 90 days":  start_date, end_date = today - timedelta(days=90), today
    else:
        start_date = st.date_input("Start", value=today - timedelta(days=30))
        end_date   = st.date_input("End",   value=today)
    st.caption(f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}")
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ga4(start: str, end: str, property_id: str):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric, OrderBy
    from google.oauth2 import service_account

    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["GA4_PROJECT_ID"],
        "private_key_id": st.secrets["GA4_PRIVATE_KEY_ID"],
        "private_key": st.secrets["GA4_PRIVATE_KEY"].replace("\\n", "\n"),
        "client_email": st.secrets["GA4_CLIENT_EMAIL"],
        "client_id": st.secrets["GA4_CLIENT_ID"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": st.secrets["GA4_CLIENT_X509_CERT_URL"],
        "universe_domain": "googleapis.com",
    }
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    client = BetaAnalyticsDataClient(credentials=credentials)
    prop = f"properties/{property_id}"

    def run(dimensions, metrics, order_bys=None, limit=20):
        return client.run_report(RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            order_bys=order_bys or [],
            limit=limit,
        ))

    # Totals
    tot_resp = run([], ["sessions","activeUsers","screenPageViews","bounceRate","averageSessionDuration"])
    row = tot_resp.rows[0].metric_values if tot_resp.rows else [None]*5

    # Daily
    daily_resp = run(["date"], ["sessions","activeUsers"],
                     [OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))])
    daily = [{"date": r.dimension_values[0].value,
               "sessions": int(r.metric_values[0].value),
               "users": int(r.metric_values[1].value)} for r in daily_resp.rows]

    # Top pages
    pg_resp = run(["pagePath"], ["screenPageViews","sessions","averageSessionDuration"],
                  [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)], 25)
    pages = [{"page": r.dimension_values[0].value,
               "views": int(r.metric_values[0].value),
               "sessions": int(r.metric_values[1].value),
               "avg_duration": float(r.metric_values[2].value)} for r in pg_resp.rows]

    # Traffic sources
    src_resp = run(["sessionDefaultChannelGroup"], ["sessions"],
                   [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)], 10)
    sources = [{"channel": r.dimension_values[0].value,
                "sessions": int(r.metric_values[0].value)} for r in src_resp.rows]

    return {
        "sessions":    int(row[0].value) if row[0] else 0,
        "users":       int(row[1].value) if row[1] else 0,
        "pageviews":   int(row[2].value) if row[2] else 0,
        "bounce_rate": float(row[3].value)*100 if row[3] else 0,
        "avg_duration":float(row[4].value) if row[4] else 0,
        "daily": daily, "pages": pages, "sources": sources,
    }


# ── Page ─────────────────────────────────────────────────────────────────────
st.markdown("## Google Analytics 4")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

start_str = start_date.strftime("%Y-%m-%d")
end_str   = end_date.strftime("%Y-%m-%d")

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

# ── KPI Cards ────────────────────────────────────────────────────────────────
def fmt_duration(s):
    m, sec = divmod(int(s), 60)
    return f"{m}m {sec:02d}s"

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(kpi_card("Sessions",     f"{data['sessions']:,}"),              unsafe_allow_html=True)
c2.markdown(kpi_card("Active Users", f"{data['users']:,}"),                 unsafe_allow_html=True)
c3.markdown(kpi_card("Page Views",   f"{data['pageviews']:,}"),             unsafe_allow_html=True)
c4.markdown(kpi_card("Bounce Rate",  f"{data['bounce_rate']:.1f}%"),        unsafe_allow_html=True)
c5.markdown(kpi_card("Avg Session",  fmt_duration(data["avg_duration"])),   unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Daily trend ──────────────────────────────────────────────────────────────
daily_df = pd.DataFrame(data["daily"])
if not daily_df.empty:
    daily_df["date"] = pd.to_datetime(daily_df["date"], format="%Y%m%d")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["sessions"], name="Sessions",
                             line=dict(color="#4CAF50", width=2.5),
                             fill="tozeroy", fillcolor="rgba(76,175,80,0.10)"))
    fig.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["users"], name="Active Users",
                             line=dict(color="#2DB896", width=2, dash="dot")))
    fig.update_layout(**chart_layout("Sessions & Active Users Over Time", "Date", "Count"))
    st.plotly_chart(fig, use_container_width=True)
st.markdown("<br>", unsafe_allow_html=True)

col_left, col_right = st.columns(2)

# ── Top pages ────────────────────────────────────────────────────────────────
pages_df = pd.DataFrame(data["pages"])
if not pages_df.empty:
    with col_left:
        top10 = pages_df.head(10)
        fig2 = go.Figure(go.Bar(
            x=top10["views"], y=top10["page"].str[:40], orientation="h",
            marker_color=COLORS[0],
            text=top10["views"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont=dict(color="#E8F5E9"),
        ))
        layout2 = chart_layout("Top 10 Pages by Views")
        layout2["yaxis"]["autorange"] = "reversed"
        fig2.update_layout(**layout2, height=420)
        st.plotly_chart(fig2, use_container_width=True)

# ── Sessions by channel donut ────────────────────────────────────────────────
sources_df = pd.DataFrame(data["sources"])
if not sources_df.empty:
    with col_right:
        fig3 = px.pie(sources_df, values="sessions", names="channel",
                      hole=0.52, color_discrete_sequence=COLORS)
        fig3.update_layout(
            **chart_layout("Sessions by Channel"),
            showlegend=True,
        )
        fig3.update_traces(textinfo="percent+label",
                           hovertemplate="%{label}: %{value:,} sessions",
                           textfont=dict(color="#E8F5E9"))
        st.plotly_chart(fig3, use_container_width=True)

# ── Top pages detail table ────────────────────────────────────────────────────
st.markdown("#### Top Pages — Detail")
if not pages_df.empty:
    display_df = pages_df.rename(columns={"page": "Page Path", "views": "Page Views",
                                          "sessions": "Sessions", "avg_duration": "Avg Duration (s)"})
    display_df["Avg Duration (s)"] = display_df["Avg Duration (s)"].apply(lambda x: f"{x:.1f}s")
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

st.markdown("---")
st.caption(f"Data source: Google Analytics 4 · Property {property_id} · Refreshed hourly")
