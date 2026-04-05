import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Search Console — Goodman Financial", page_icon="🔍",
                   layout="wide", initial_sidebar_state="expanded")

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

def kpi_card(title, value, delta=None, lower_is_better=False):
    delta_html = ""
    if delta is not None:
        positive = (delta >= 0 and not lower_is_better) or (delta < 0 and lower_is_better)
        clr = "#4CAF50" if positive else "#EF5350"
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
        creds_dict, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    service = build("searchconsole", "v1", credentials=credentials)

    def query(dimensions, row_limit=25):
        return service.searchanalytics().query(
            siteUrl=site_url,
            body={"startDate": start, "endDate": end, "dimensions": dimensions, "rowLimit": row_limit},
        ).execute()

    totals_row = query([]).get("rows", [{}])[0]

    daily_rows = [{"date": r["keys"][0], "clicks": int(r["clicks"]),
                   "impressions": int(r["impressions"]), "ctr": r["ctr"]*100, "position": r["position"]}
                  for r in query(["date"], 90).get("rows", [])]

    queries_rows = [{"query": r["keys"][0], "clicks": int(r["clicks"]),
                     "impressions": int(r["impressions"]), "ctr": round(r["ctr"]*100,2), "position": round(r["position"],1)}
                    for r in query(["query"], 50).get("rows", [])]

    pages_rows = [{"page": r["keys"][0], "clicks": int(r["clicks"]),
                   "impressions": int(r["impressions"]), "ctr": round(r["ctr"]*100,2), "position": round(r["position"],1)}
                  for r in query(["page"], 50).get("rows", [])]

    return {
        "clicks":      int(totals_row.get("clicks", 0)),
        "impressions": int(totals_row.get("impressions", 0)),
        "ctr":         totals_row.get("ctr", 0) * 100,
        "position":    totals_row.get("position", 0),
        "daily": daily_rows, "queries": queries_rows, "pages": pages_rows,
    }


# ── Page ─────────────────────────────────────────────────────────────────────
st.markdown("## Google Search Console")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}** · Google organic only")
st.markdown("---")

start_str = start_date.strftime("%Y-%m-%d")
end_str   = end_date.strftime("%Y-%m-%d")

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

# ── KPI Cards ────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_card("Total Clicks",  f"{data['clicks']:,}"),          unsafe_allow_html=True)
c2.markdown(kpi_card("Impressions",   f"{data['impressions']:,}"),      unsafe_allow_html=True)
c3.markdown(kpi_card("Avg CTR",       f"{data['ctr']:.2f}%"),           unsafe_allow_html=True)
c4.markdown(kpi_card("Avg Position",  f"{data['position']:.1f}", lower_is_better=True), unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Daily trend ──────────────────────────────────────────────────────────────
daily_df = pd.DataFrame(data["daily"])
if not daily_df.empty:
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    tab1, tab2 = st.tabs(["Clicks & Impressions", "CTR & Position"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=daily_df["date"], y=daily_df["impressions"],
                             name="Impressions", marker_color="rgba(76,175,80,0.18)", yaxis="y2"))
        fig.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["clicks"],
                                 name="Clicks", line=dict(color="#4CAF50", width=2.5)))
        layout_args = chart_layout("Clicks vs Impressions", "Date")
        layout_args["barmode"] = "overlay"
        layout_args["yaxis"]  = dict(title="Clicks", gridcolor="#1A2E22", color="#9AC89E",
                                     tickfont=dict(color="#9AC89E"), title_font=dict(color="#9AC89E"))
        layout_args["yaxis2"] = dict(title="Impressions", overlaying="y", side="right",
                                     gridcolor="rgba(0,0,0,0)", color="#9AC89E",
                                     tickfont=dict(color="#9AC89E"), title_font=dict(color="#9AC89E"))
        fig.update_layout(**layout_args)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["ctr"],
                                  name="CTR (%)", line=dict(color="#4CAF50", width=2.5)))
        fig2.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["position"],
                                  name="Avg Position", line=dict(color="#2DB896", width=2, dash="dot"),
                                  yaxis="y2"))
        layout_args2 = chart_layout("CTR & Avg Position", "Date")
        layout_args2["yaxis"]  = dict(title="CTR (%)", gridcolor="#1A2E22", color="#9AC89E",
                                      tickfont=dict(color="#9AC89E"), title_font=dict(color="#9AC89E"))
        layout_args2["yaxis2"] = dict(title="Avg Position (lower = better)", overlaying="y", side="right",
                                      autorange="reversed", gridcolor="rgba(0,0,0,0)", color="#9AC89E",
                                      tickfont=dict(color="#9AC89E"), title_font=dict(color="#9AC89E"))
        fig2.update_layout(**layout_args2)
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
col_left, col_right = st.columns(2)

# ── Top queries bar ──────────────────────────────────────────────────────────
queries_df = pd.DataFrame(data["queries"])
if not queries_df.empty:
    with col_left:
        top10 = queries_df.head(10)
        fig3 = go.Figure(go.Bar(
            x=top10["clicks"], y=top10["query"].str[:45], orientation="h",
            marker_color=COLORS[0],
            text=top10["clicks"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont=dict(color="#E8F5E9"),
        ))
        layout3 = chart_layout("Top Queries by Clicks")
        layout3["yaxis"]["autorange"] = "reversed"
        fig3.update_layout(**layout3, height=400)
        st.plotly_chart(fig3, use_container_width=True)

# ── Top pages bar ─────────────────────────────────────────────────────────────
pages_df = pd.DataFrame(data["pages"])
if not pages_df.empty:
    with col_right:
        top10p = pages_df.head(10).copy()
        top10p["page_short"] = top10p["page"].str.replace(r"https?://[^/]+", "", regex=True).str[:45]
        fig4 = go.Figure(go.Bar(
            x=top10p["clicks"], y=top10p["page_short"], orientation="h",
            marker_color=COLORS[1],
            text=top10p["clicks"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont=dict(color="#E8F5E9"),
        ))
        layout4 = chart_layout("Top Pages by Clicks")
        layout4["yaxis"]["autorange"] = "reversed"
        fig4.update_layout(**layout4, height=400)
        st.plotly_chart(fig4, use_container_width=True)

# ── Detail tables ─────────────────────────────────────────────────────────────
st.markdown("#### Top Queries — Detail")
if not queries_df.empty:
    st.dataframe(queries_df.rename(columns={"query": "Query", "clicks": "Clicks",
                                            "impressions": "Impressions", "ctr": "CTR (%)", "position": "Avg Position"}),
                 use_container_width=True, hide_index=True, height=400)

st.markdown("#### Top Pages — Detail")
if not pages_df.empty:
    st.dataframe(pages_df.rename(columns={"page": "Page URL", "clicks": "Clicks",
                                          "impressions": "Impressions", "ctr": "CTR (%)", "position": "Avg Position"}),
                 use_container_width=True, hide_index=True, height=400)

st.markdown("---")
st.caption(f"Data source: Google Search Console · {site_url} · Refreshed hourly")
