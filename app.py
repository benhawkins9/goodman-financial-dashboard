import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import json

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="Goodman Financial — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme / CSS ─────────────────────────────────────────────────────────────
def apply_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    #MainMenu, footer, header { visibility: hidden; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0F6E56; }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: rgba(255,255,255,0.92) !important; }
    [data-testid="stSidebar"] a { color: #A8E6D6 !important; }
    [data-testid="stSidebarNav"] a:hover { background-color: rgba(255,255,255,0.12) !important; }
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: rgba(255,255,255,0.18) !important;
        border-left: 3px solid white;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: #0F6E56 !important;
        border-color: #0F6E56 !important;
        color: white !important;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #0A4F3E !important;
        border-color: #0A4F3E !important;
    }

    /* Metric labels */
    [data-testid="stMetricLabel"] { color: #555 !important; font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] { color: #0F6E56 !important; font-weight: 700 !important; }
    [data-testid="stMetricDelta"] svg { display: none; }

    /* Page headings */
    h1 { color: #0F6E56 !important; font-weight: 700; }
    h2 { color: #0F6E56 !important; font-weight: 600; }
    h3 { color: #1A1A1A !important; font-weight: 600; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #E0EDE9; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 3px solid #0F6E56;
        color: #0F6E56;
        font-weight: 600;
    }

    /* DataFrames */
    [data-testid="stDataFrame"] { border: 1px solid #E0EDE9; border-radius: 8px; }

    /* Divider */
    hr { border-color: #E0EDE9 !important; }
    </style>
    """, unsafe_allow_html=True)


def kpi_card(title: str, value: str, delta: float | None = None, delta_suffix: str = "vs prev period"):
    if delta is not None:
        clr = "#1B8E4B" if delta >= 0 else "#C0392B"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<p style="color:{clr};font-size:0.82rem;margin:4px 0 0;">{arrow} {abs(delta):.1f}% {delta_suffix}</p>'
    else:
        delta_html = ""
    return f"""
    <div style="background:#F4FBF8;border:1px solid #D4EDE5;border-left:4px solid #0F6E56;
                border-radius:8px;padding:1.1rem 1.25rem;height:100%;">
        <p style="color:#6B7280;font-size:0.75rem;text-transform:uppercase;
                  letter-spacing:0.06em;margin:0 0 6px;">{title}</p>
        <h2 style="color:#0F2A22;font-size:1.7rem;font-weight:700;margin:0;">{value}</h2>
        {delta_html}
    </div>"""


def source_badge(label: str, connected: bool):
    if connected:
        return f'<span style="background:#D4EDDA;color:#1B6B35;padding:2px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;">✓ {label}</span>'
    return f'<span style="background:#FDE8E8;color:#9B2828;padding:2px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;">✗ {label}</span>'


# ── Auth ─────────────────────────────────────────────────────────────────────
apply_theme()

def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center;padding:3rem 0 1.5rem;">
            <div style="width:64px;height:64px;background:#0F6E56;border-radius:12px;
                        display:inline-flex;align-items:center;justify-content:center;
                        font-size:2rem;margin-bottom:1rem;">📊</div>
            <h1 style="color:#0F6E56;margin:0;font-size:1.8rem;">Goodman Financial</h1>
            <p style="color:#6B7280;margin:0.4rem 0 2rem;font-size:0.95rem;">Marketing Analytics Dashboard</p>
        </div>
        """, unsafe_allow_html=True)

        pwd = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="collapsed")

        if st.button("Sign In", use_container_width=True, type="primary"):
            if pwd == st.secrets.get("APP_PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password — please try again.")

        st.markdown('<p style="text-align:center;color:#9CA3AF;font-size:0.75rem;margin-top:2rem;">© 2025 Goodman Financial</p>', unsafe_allow_html=True)
    return False


if not check_password():
    st.stop()


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Goodman Financial")
    st.markdown("---")
    st.markdown("**Navigation**")
    st.markdown("Use the pages above to explore each channel.")
    st.markdown("---")

    # Date range
    st.markdown("**Overview Date Range**")
    range_opt = st.selectbox(
        "Range",
        ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
        index=1,
        label_visibility="collapsed",
    )
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


# ── Helpers ──────────────────────────────────────────────────────────────────
def fmt_number(n, decimals=0):
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,.{decimals}f}"


def fmt_currency(n):
    if n is None:
        return "—"
    return f"${n:,.2f}"


def fmt_pct(n):
    if n is None:
        return "—"
    return f"{n:.2f}%"


# ── Data fetchers (each wrapped in try/except) ────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ga4_summary(start: str, end: str) -> dict:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
    from google.oauth2 import service_account

    creds_info = json.loads(st.secrets["GA4_CREDENTIALS"])
    creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    credentials = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=credentials)
    request = RunReportRequest(
        property=f"properties/{st.secrets['GA4_PROPERTY_ID']}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews"),
        ],
    )
    resp = client.run_report(request)
    row = resp.rows[0].metric_values if resp.rows else None
    return {
        "sessions": int(row[0].value) if row else 0,
        "users": int(row[1].value) if row else 0,
        "pageviews": int(row[2].value) if row else 0,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_gsc_summary(start: str, end: str) -> dict:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account

    creds_info = json.loads(st.secrets["GA4_CREDENTIALS"])
    creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    credentials = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = build("searchconsole", "v1", credentials=credentials)
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": [],
    }
    result = service.searchanalytics().query(siteUrl=st.secrets["GSC_SITE_URL"], body=body).execute()
    row = result.get("rows", [{}])[0]
    return {
        "clicks": int(row.get("clicks", 0)),
        "impressions": int(row.get("impressions", 0)),
        "ctr": row.get("ctr", 0) * 100,
        "position": row.get("position", 0),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_meta_summary(start: str, end: str) -> dict:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount

    FacebookAdsApi.init(access_token=st.secrets["META_ACCESS_TOKEN"])
    account = AdAccount(st.secrets["META_AD_ACCOUNT_ID"])
    insights = account.get_insights(
        fields=["spend", "impressions", "clicks", "ctr", "cpc"],
        params={
            "time_range": {"since": start, "until": end},
            "level": "account",
        },
    )
    row = dict(list(insights)[0]) if insights else {}
    return {
        "spend": float(row.get("spend", 0)),
        "impressions": int(row.get("impressions", 0)),
        "clicks": int(row.get("clicks", 0)),
        "ctr": float(row.get("ctr", 0)),
        "cpc": float(row.get("cpc", 0)),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_linkedin_summary() -> dict:
    import gspread
    from google.oauth2.service_account import Credentials

    creds_info = json.loads(st.secrets["GA4_CREDENTIALS"])
    creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(st.secrets["LINKEDIN_SHEET_ID"])
    ws = sheet.get_worksheet(0)
    df = pd.DataFrame(ws.get_all_records())
    out = {"rows": len(df)}
    for col in ["Impressions", "Clicks", "Spend", "impressions", "clicks", "spend"]:
        if col in df.columns:
            out[col.lower()] = pd.to_numeric(df[col], errors="coerce").sum()
    return out


# ── Main content ─────────────────────────────────────────────────────────────
st.markdown("## Overview")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}** &nbsp;|&nbsp; All channels at a glance")
st.markdown("---")

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

# ── GA4 ──
ga4_data, ga4_ok = None, False
with st.spinner("Loading GA4…"):
    try:
        ga4_data = fetch_ga4_summary(start_str, end_str)
        ga4_ok = True
    except Exception as e:
        ga4_err = str(e)

# ── GSC ──
gsc_data, gsc_ok = None, False
with st.spinner("Loading Search Console…"):
    try:
        gsc_data = fetch_gsc_summary(start_str, end_str)
        gsc_ok = True
    except Exception as e:
        gsc_err = str(e)

# ── Meta ──
meta_data, meta_ok = None, False
with st.spinner("Loading Facebook Ads…"):
    try:
        meta_data = fetch_meta_summary(start_str, end_str)
        meta_ok = True
    except Exception as e:
        meta_err = str(e)

# ── LinkedIn ──
li_data, li_ok = None, False
with st.spinner("Loading LinkedIn…"):
    try:
        li_data = fetch_linkedin_summary()
        li_ok = True
    except Exception as e:
        li_err = str(e)

# Connection badges
badges = (
    source_badge("GA4", ga4_ok) + " &nbsp; " +
    source_badge("Search Console", gsc_ok) + " &nbsp; " +
    source_badge("Google Ads", False) + " &nbsp; " +
    source_badge("Facebook Ads", meta_ok) + " &nbsp; " +
    source_badge("LinkedIn", li_ok)
)
st.markdown(badges, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── GA4 KPIs ──
st.markdown("#### Website (GA4)")
c1, c2, c3 = st.columns(3)
if ga4_ok and ga4_data:
    c1.markdown(kpi_card("Sessions", fmt_number(ga4_data["sessions"])), unsafe_allow_html=True)
    c2.markdown(kpi_card("Active Users", fmt_number(ga4_data["users"])), unsafe_allow_html=True)
    c3.markdown(kpi_card("Page Views", fmt_number(ga4_data["pageviews"])), unsafe_allow_html=True)
else:
    with c1:
        st.warning(f"GA4 not connected{': ' + ga4_err[:80] if 'ga4_err' in dir() else '.'}")

st.markdown("<br>", unsafe_allow_html=True)

# ── GSC KPIs ──
st.markdown("#### Organic Search (Google Search Console)")
c1, c2, c3, c4 = st.columns(4)
if gsc_ok and gsc_data:
    c1.markdown(kpi_card("Clicks", fmt_number(gsc_data["clicks"])), unsafe_allow_html=True)
    c2.markdown(kpi_card("Impressions", fmt_number(gsc_data["impressions"])), unsafe_allow_html=True)
    c3.markdown(kpi_card("Avg CTR", fmt_pct(gsc_data["ctr"])), unsafe_allow_html=True)
    c4.markdown(kpi_card("Avg Position", f'{gsc_data["position"]:.1f}'), unsafe_allow_html=True)
else:
    with c1:
        st.warning(f"Search Console not connected{': ' + gsc_err[:80] if 'gsc_err' in dir() else '.'}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Meta KPIs ──
st.markdown("#### Paid Social (Facebook / Meta Ads)")
c1, c2, c3, c4, c5 = st.columns(5)
if meta_ok and meta_data:
    c1.markdown(kpi_card("Spend", fmt_currency(meta_data["spend"])), unsafe_allow_html=True)
    c2.markdown(kpi_card("Impressions", fmt_number(meta_data["impressions"])), unsafe_allow_html=True)
    c3.markdown(kpi_card("Clicks", fmt_number(meta_data["clicks"])), unsafe_allow_html=True)
    c4.markdown(kpi_card("CTR", fmt_pct(meta_data["ctr"])), unsafe_allow_html=True)
    c5.markdown(kpi_card("CPC", fmt_currency(meta_data["cpc"])), unsafe_allow_html=True)
else:
    with c1:
        st.warning(f"Facebook Ads not connected{': ' + meta_err[:80] if 'meta_err' in dir() else '.'}")

st.markdown("<br>", unsafe_allow_html=True)

# ── LinkedIn KPIs ──
st.markdown("#### LinkedIn")
if li_ok and li_data:
    cols = st.columns(min(len(li_data), 4))
    items = list(li_data.items())
    for i, (k, v) in enumerate(items[:4]):
        label = k.replace("_", " ").title()
        val = fmt_currency(v) if "spend" in k else fmt_number(v) if isinstance(v, (int, float)) else str(v)
        cols[i].markdown(kpi_card(label, val), unsafe_allow_html=True)
else:
    st.warning(f"LinkedIn (Google Sheet) not connected{': ' + li_err[:80] if 'li_err' in dir() else '.'}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Google Ads placeholder ──
st.markdown("#### Paid Search (Google Ads)")
st.info("Google Ads is not yet connected. Navigate to the **Google Ads** page for setup instructions.", icon="ℹ️")

st.markdown("---")
st.caption(f"Dashboard refreshes every hour. Data as of {datetime.now().strftime('%b %d, %Y %I:%M %p')}.")
