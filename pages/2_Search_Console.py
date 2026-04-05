import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd


st.set_page_config(
    page_title="Search Console — Goodman Financial",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

COLORS = ["#0F6E56", "#1A9E7A", "#2DB896", "#5DCFB2", "#88E5CD", "#B4F0E0"]

def kpi_card(title, value, delta=None, lower_is_better=False):
    delta_html = ""
    if delta is not None:
        positive = (delta >= 0 and not lower_is_better) or (delta < 0 and lower_is_better)
        clr = "#1B8E4B" if positive else "#C0392B"
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
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", color="#374151"),
        xaxis=dict(title=xaxis_title, gridcolor="#F3F4F6", linecolor="#E5E7EB"),
        yaxis=dict(title=yaxis_title, gridcolor="#F3F4F6", linecolor="#E5E7EB"),
        margin=dict(t=50, b=40, l=50, r=20),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
    )


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


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_gsc(start: str, end: str, site_url: str):
    from googleapiclient.discovery import build
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
        creds_dict,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = build("searchconsole", "v1", credentials=credentials)

    def query(dimensions, row_limit=25):
        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": dimensions,
            "rowLimit": row_limit,
        }
        return service.searchanalytics().query(siteUrl=site_url, body=body).execute()

    # Summary totals
    totals_resp = query([])
    totals_row = totals_resp.get("rows", [{}])[0]

    # Daily trend
    daily_resp = query(["date"], row_limit=90)
    daily_rows = [
        {
            "date": r["keys"][0],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": r["ctr"] * 100,
            "position": r["position"],
        }
        for r in daily_resp.get("rows", [])
    ]

    # Top queries
    queries_resp = query(["query"], row_limit=20)
    queries_rows = [
        {
            "query": r["keys"][0],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1),
        }
        for r in queries_resp.get("rows", [])
    ]

    # Top pages
    pages_resp = query(["page"], row_limit=20)
    pages_rows = [
        {
            "page": r["keys"][0],
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "ctr": round(r["ctr"] * 100, 2),
            "position": round(r["position"], 1),
        }
        for r in pages_resp.get("rows", [])
    ]

    return {
        "clicks": int(totals_row.get("clicks", 0)),
        "impressions": int(totals_row.get("impressions", 0)),
        "ctr": totals_row.get("ctr", 0) * 100,
        "position": totals_row.get("position", 0),
        "daily": daily_rows,
        "queries": queries_rows,
        "pages": pages_rows,
    }


# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown("## Google Search Console")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

try:
    site_url = st.secrets["GSC_SITE_URL"]
except KeyError:
    st.error("GSC_SITE_URL is missing from secrets.toml")
    st.stop()

with st.spinner("Fetching Search Console data…"):
    try:
        data = fetch_gsc(start_str, end_str, site_url)
    except Exception as e:
        st.error(f"Could not load Search Console data: {e}")
        st.stop()

# ── KPI Cards ──
c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_card("Total Clicks", f"{data['clicks']:,}"), unsafe_allow_html=True)
c2.markdown(kpi_card("Impressions", f"{data['impressions']:,}"), unsafe_allow_html=True)
c3.markdown(kpi_card("Avg CTR", f"{data['ctr']:.2f}%"), unsafe_allow_html=True)
c4.markdown(kpi_card("Avg Position", f"{data['position']:.1f}", lower_is_better=True), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Daily trend ──
daily_df = pd.DataFrame(data["daily"])
if not daily_df.empty:
    daily_df["date"] = pd.to_datetime(daily_df["date"])

    tab1, tab2 = st.tabs(["Clicks & Impressions", "CTR & Position"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily_df["date"], y=daily_df["impressions"],
            name="Impressions", marker_color="rgba(15,110,86,0.2)",
            yaxis="y2",
        ))
        fig.add_trace(go.Scatter(
            x=daily_df["date"], y=daily_df["clicks"],
            name="Clicks", line=dict(color="#0F6E56", width=2.5),
        ))
        fig.update_layout(
            **chart_layout("Clicks vs Impressions", "Date"),
            yaxis=dict(title="Clicks", gridcolor="#F3F4F6"),
            yaxis2=dict(title="Impressions", overlaying="y", side="right", gridcolor="rgba(0,0,0,0)"),
            barmode="overlay",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=daily_df["date"], y=daily_df["ctr"],
            name="CTR (%)", line=dict(color="#0F6E56", width=2.5),
        ))
        fig2.add_trace(go.Scatter(
            x=daily_df["date"], y=daily_df["position"],
            name="Avg Position", line=dict(color="#1A9E7A", width=2, dash="dot"),
            yaxis="y2",
        ))
        fig2.update_layout(
            **chart_layout("CTR & Avg Position", "Date"),
            yaxis=dict(title="CTR (%)", gridcolor="#F3F4F6"),
            yaxis2=dict(title="Avg Position (lower = better)", overlaying="y", side="right",
                        autorange="reversed", gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
col_left, col_right = st.columns(2)

# ── Top queries bar chart ──
queries_df = pd.DataFrame(data["queries"])
if not queries_df.empty:
    with col_left:
        top10 = queries_df.head(10)
        fig3 = go.Figure(go.Bar(
            x=top10["clicks"],
            y=top10["query"].str[:45],
            orientation="h",
            marker_color=COLORS[0],
            text=top10["clicks"].apply(lambda v: f"{v:,}"),
            textposition="outside",
        ))
        fig3.update_layout(**chart_layout("Top Queries by Clicks"))
        fig3.update_layout(yaxis=dict(autorange="reversed"), height=400)
        st.plotly_chart(fig3, use_container_width=True)

# ── Top pages bar chart ──
pages_df = pd.DataFrame(data["pages"])
if not pages_df.empty:
    with col_right:
        top10p = pages_df.head(10)
        # Strip protocol from URLs for display
        top10p = top10p.copy()
        top10p["page_short"] = top10p["page"].str.replace(r"https?://[^/]+", "", regex=True).str[:45]
        fig4 = go.Figure(go.Bar(
            x=top10p["clicks"],
            y=top10p["page_short"],
            orientation="h",
            marker_color=COLORS[1],
            text=top10p["clicks"].apply(lambda v: f"{v:,}"),
            textposition="outside",
        ))
        fig4.update_layout(**chart_layout("Top Pages by Clicks"))
        fig4.update_layout(yaxis=dict(autorange="reversed"), height=400)
        st.plotly_chart(fig4, use_container_width=True)

# ── Data tables ──
st.markdown("#### Top Queries — Detail")
if not queries_df.empty:
    st.dataframe(
        queries_df.rename(columns={"query": "Query", "clicks": "Clicks",
                                   "impressions": "Impressions", "ctr": "CTR (%)", "position": "Avg Position"}),
        use_container_width=True, hide_index=True,
    )

st.markdown("#### Top Pages — Detail")
if not pages_df.empty:
    st.dataframe(
        pages_df.rename(columns={"page": "Page URL", "clicks": "Clicks",
                                 "impressions": "Impressions", "ctr": "CTR (%)", "position": "Avg Position"}),
        use_container_width=True, hide_index=True,
    )

st.markdown("---")
st.caption(f"Data source: Google Search Console · {site_url} · Refreshed hourly")
