import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="Goodman Financial — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark Theme CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}

.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main,.block-container{
    background-color:#0F1A14!important;}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span{color:#E8F5E9!important;}
.stCaption,[data-testid="stCaptionContainer"]{color:#9AC89E!important;}
label{color:#9AC89E!important;}
h1{color:#E8F5E9!important;font-weight:700;}
h2{color:#E8F5E9!important;font-weight:600;}
h3,h4{color:#9AC89E!important;font-weight:600;}

[data-testid="stSidebar"]{background-color:#0F6E56!important;}
[data-testid="stSidebar"] *{color:rgba(255,255,255,0.92)!important;}
[data-testid="stSidebar"] a{color:#A8E6D6!important;}
[data-testid="stSidebarNav"] a:hover{background-color:rgba(255,255,255,0.12)!important;}
[data-testid="stSidebarNav"] a[aria-selected="true"]{
    background-color:rgba(255,255,255,0.18)!important;border-left:3px solid white;}

.stButton>button[kind="primary"]{background-color:#4CAF50!important;border-color:#4CAF50!important;
    color:#0F1A14!important;font-weight:700;border-radius:6px;}
.stButton>button[kind="primary"]:hover{background-color:#43A047!important;border-color:#43A047!important;}
.stButton>button:not([kind="primary"]){background-color:#1A2E22!important;border-color:#2A4A35!important;
    color:#E8F5E9!important;border-radius:6px;}

.stTabs [data-baseweb="tab-list"]{background-color:transparent;border-bottom:2px solid #2A4A35;}
.stTabs [data-baseweb="tab"]{color:#9AC89E!important;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{
    border-bottom:3px solid #4CAF50!important;color:#E8F5E9!important;font-weight:600;}

[data-testid="stDataFrame"]{border:1px solid #2A4A35;border-radius:8px;}
[data-testid="stAlert"]{background-color:#1A2E22!important;border-color:#2A4A35!important;}
hr{border-color:#2A4A35!important;}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def kpi_card(title: str, value: str, delta: float | None = None, muted: bool = False):
    val_color = "#9AC89E" if muted else "#4CAF50"
    delta_html = ""
    if delta is not None:
        clr = "#4CAF50" if delta >= 0 else "#EF5350"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<p style="color:{clr};font-size:0.82rem;margin:4px 0 0;">{arrow} {abs(delta):.1f}%</p>'
    return f"""<div style="background:#1A2E22;border:1px solid #2A4A35;border-left:4px solid #4CAF50;
                border-radius:8px;padding:1.1rem 1.25rem;height:100%;">
        <p style="color:#9AC89E;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 6px;">{title}</p>
        <h2 style="color:{val_color};font-size:1.7rem;font-weight:700;margin:0;">{value}</h2>
        {delta_html}</div>"""


def cpl_card(title: str, value: str, connected: bool = True):
    border = "#4CAF50" if connected else "#555"
    val_color = "#4CAF50" if connected else "#9AC89E"
    sub = "" if connected else '<p style="color:#9AC89E;font-size:0.78rem;margin:4px 0 0;">Not connected</p>'
    return f"""<div style="background:#1A2E22;border:1px solid #2A4A35;border-left:4px solid {border};
                border-radius:8px;padding:1.1rem 1.25rem;height:100%;">
        <p style="color:#9AC89E;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 6px;">{title}</p>
        <h2 style="color:{val_color};font-size:1.7rem;font-weight:700;margin:0;">{value}</h2>
        {sub}</div>"""


def source_badge(label: str, connected: bool):
    if connected:
        return f'<span style="background:rgba(76,175,80,0.15);color:#4CAF50;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;border:1px solid rgba(76,175,80,0.3);">✓ {label}</span>'
    return f'<span style="background:rgba(239,83,80,0.12);color:#EF9A9A;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;border:1px solid rgba(239,83,80,0.2);">✗ {label}</span>'


def fmt_number(n, decimals=0):
    if n is None: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return f"{n:,.{decimals}f}"

def fmt_currency(n):
    if n is None: return "—"
    return f"${n:,.2f}"

def fmt_pct(n):
    if n is None: return "—"
    return f"{n:.2f}%"


# ── Auth ──────────────────────────────────────────────────────────────────────
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
            <h1 style="color:#E8F5E9;margin:0;font-size:1.8rem;">Goodman Financial</h1>
            <p style="color:#9AC89E;margin:0.4rem 0 2rem;font-size:0.95rem;">Marketing Analytics Dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="collapsed")
        if st.button("Sign In", use_container_width=True, type="primary"):
            if pwd == st.secrets.get("APP_PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password — please try again.")
        st.markdown('<p style="text-align:center;color:#9AC89E;font-size:0.75rem;margin-top:2rem;">© 2025 Goodman Financial</p>', unsafe_allow_html=True)
    return False

if not check_password():
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Goodman Financial")
    st.markdown("---")
    st.markdown("**Overview Date Range**")
    range_opt = st.selectbox("Range", ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
                             index=1, label_visibility="collapsed")
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


# ── Data fetchers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ga4_summary(start: str, end: str) -> dict:
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

    # Totals
    req = RunReportRequest(
        property=f"properties/{st.secrets['GA4_PROPERTY_ID']}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers"), Metric(name="screenPageViews")],
    )
    resp = client.run_report(req)
    row = resp.rows[0].metric_values if resp.rows else None

    # Channel breakdown
    ch_req = RunReportRequest(
        property=f"properties/{st.secrets['GA4_PROPERTY_ID']}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=8,
    )
    ch_resp = client.run_report(ch_req)
    channels = [{"channel": r.dimension_values[0].value, "sessions": int(r.metric_values[0].value)}
                for r in ch_resp.rows]

    return {
        "sessions": int(row[0].value) if row else 0,
        "users": int(row[1].value) if row else 0,
        "pageviews": int(row[2].value) if row else 0,
        "channels": channels,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_gsc_summary(start: str, end: str) -> dict:
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
    result = service.searchanalytics().query(
        siteUrl=st.secrets["GSC_SITE_URL"],
        body={"startDate": start, "endDate": end, "dimensions": []},
    ).execute()
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
    FacebookAdsApi.init(access_token=st.secrets["META_ACCESS_TOKEN"].strip())
    account = AdAccount(st.secrets["META_AD_ACCOUNT_ID"].strip())
    rows = list(account.get_insights(
        fields=["spend", "impressions", "clicks", "ctr", "cpc", "actions"],
        params={"time_range": {"since": start, "until": end}, "level": "account"},
    ))
    row = dict(rows[0]) if rows else {}
    actions = row.get("actions", [])
    leads = sum(int(a.get("value", 0)) for a in actions
                if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead",
                                            "offsite_conversion.fb_pixel_purchase", "purchase"))
    return {
        "spend": float(row.get("spend", 0)),
        "impressions": int(row.get("impressions", 0)),
        "clicks": int(row.get("clicks", 0)),
        "ctr": float(row.get("ctr", 0)),
        "cpc": float(row.get("cpc", 0)),
        "leads": leads,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_linkedin_summary() -> dict:
    import gspread
    from google.oauth2.service_account import Credentials
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
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(st.secrets["LINKEDIN_SHEET_ID"]).get_worksheet(0)
    df = pd.DataFrame(ws.get_all_records())
    out = {"rows": len(df)}
    for col in ["Impressions", "impressions"]:
        if col in df.columns:
            out["impressions"] = pd.to_numeric(df[col], errors="coerce").sum(); break
    for col in ["Clicks", "clicks", "Link Clicks"]:
        if col in df.columns:
            out["clicks"] = pd.to_numeric(df[col], errors="coerce").sum(); break
    for col in ["Spend", "spend", "Amount Spent", "Cost"]:
        if col in df.columns:
            out["spend"] = pd.to_numeric(df[col], errors="coerce").sum(); break
    for col in ["Leads", "leads", "Conversions", "conversions", "Form Submissions"]:
        if col in df.columns:
            out["leads"] = pd.to_numeric(df[col], errors="coerce").sum(); break
    return out


# ── Page content ──────────────────────────────────────────────────────────────
start_str = start_date.strftime("%Y-%m-%d")
end_str   = end_date.strftime("%Y-%m-%d")

st.markdown("# Goodman Financial — Channel Performance")
st.markdown(f'<p style="color:#9AC89E;margin-top:-0.5rem;">{start_date.strftime("%B %d")} – {end_date.strftime("%B %d, %Y")}</p>',
            unsafe_allow_html=True)
st.markdown("---")

# ── Fetch all sources ─────────────────────────────────────────────────────────
ga4_data, ga4_ok, ga4_err   = None, False, ""
gsc_data, gsc_ok, gsc_err   = None, False, ""
meta_data, meta_ok, meta_err = None, False, ""
li_data,  li_ok,  li_err    = None, False, ""

with st.spinner("Loading data from all channels…"):
    try:
        ga4_data  = fetch_ga4_summary(start_str, end_str);  ga4_ok  = True
    except Exception as e: ga4_err  = str(e)
    try:
        gsc_data  = fetch_gsc_summary(start_str, end_str);  gsc_ok  = True
    except Exception as e: gsc_err  = str(e)
    try:
        meta_data = fetch_meta_summary(start_str, end_str); meta_ok = True
    except Exception as e: meta_err = str(e)
    try:
        li_data   = fetch_linkedin_summary();               li_ok   = True
    except Exception as e: li_err   = str(e)

# Connection badges
badges = " &nbsp; ".join([
    source_badge("GA4", ga4_ok),
    source_badge("Search Console", gsc_ok),
    source_badge("Google Ads", False),
    source_badge("Facebook Ads", meta_ok),
    source_badge("LinkedIn", li_ok),
])
st.markdown(badges, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Derive aggregates ─────────────────────────────────────────────────────────
total_sessions = ga4_data["sessions"] if ga4_ok and ga4_data else None
fb_spend   = meta_data["spend"]   if meta_ok and meta_data else 0.0
fb_leads   = meta_data["leads"]   if meta_ok and meta_data else 0
li_spend   = float(li_data.get("spend", 0))  if li_ok and li_data else 0.0
li_leads   = int(li_data.get("leads", 0))    if li_ok and li_data else 0
total_spend = fb_spend + li_spend
total_leads = fb_leads + li_leads
blended_cpl = (total_spend / total_leads) if total_leads > 0 else None

# ── 4 Summary KPI cards ──────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_card("Total Sessions", fmt_number(total_sessions) if total_sessions is not None else "—",
                     muted=not ga4_ok), unsafe_allow_html=True)
c2.markdown(kpi_card("Total Leads", fmt_number(total_leads) if (meta_ok or li_ok) else "—",
                     muted=not (meta_ok or li_ok)), unsafe_allow_html=True)
c3.markdown(kpi_card("Total Ad Spend", fmt_currency(total_spend) if (meta_ok or li_ok) else "—",
                     muted=not (meta_ok or li_ok)), unsafe_allow_html=True)
c4.markdown(kpi_card("Blended CPL", fmt_currency(blended_cpl) if blended_cpl else "—",
                     muted=blended_cpl is None), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Bar charts ───────────────────────────────────────────────────────────────
CHART_BG = "#0F1A14"
COLORS   = ["#4CAF50", "#2DB896", "#66BB6A", "#81C784", "#1A9E7A"]

col_left, col_right = st.columns(2)

# Sessions by channel (from GA4 channel breakdown)
with col_left:
    if ga4_ok and ga4_data and ga4_data.get("channels"):
        ch_df = pd.DataFrame(ga4_data["channels"]).sort_values("sessions")
        fig = go.Figure(go.Bar(
            x=ch_df["sessions"], y=ch_df["channel"],
            orientation="h",
            marker_color=COLORS[0],
            text=ch_df["sessions"].apply(lambda v: f"{v:,}"),
            textposition="outside",
            textfont=dict(color="#E8F5E9"),
        ))
        fig.update_layout(
            title=dict(text="Sessions by Channel", font=dict(size=14, color="#E8F5E9"), x=0),
            plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
            font=dict(color="#E8F5E9"),
            xaxis=dict(gridcolor="#1A2E22", linecolor="#2A4A35", color="#9AC89E", tickfont=dict(color="#9AC89E")),
            yaxis=dict(gridcolor="#1A2E22", linecolor="#2A4A35", color="#9AC89E", tickfont=dict(color="#9AC89E")),
            margin=dict(t=40, b=20, l=10, r=60),
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown(kpi_card("Sessions by Channel", "GA4 not connected", muted=True), unsafe_allow_html=True)

# Leads by channel
with col_right:
    lead_channels, lead_values = [], []
    if meta_ok and fb_leads > 0:
        lead_channels.append("Facebook Ads"); lead_values.append(fb_leads)
    if li_ok and li_leads > 0:
        lead_channels.append("LinkedIn"); lead_values.append(li_leads)

    if lead_channels:
        fig2 = go.Figure(go.Bar(
            x=lead_values, y=lead_channels,
            orientation="h",
            marker_color=COLORS[1],
            text=lead_values,
            textposition="outside",
            textfont=dict(color="#E8F5E9"),
        ))
        fig2.update_layout(
            title=dict(text="Leads by Channel", font=dict(size=14, color="#E8F5E9"), x=0),
            plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
            font=dict(color="#E8F5E9"),
            xaxis=dict(gridcolor="#1A2E22", linecolor="#2A4A35", color="#9AC89E", tickfont=dict(color="#9AC89E")),
            yaxis=dict(gridcolor="#1A2E22", linecolor="#2A4A35", color="#9AC89E", tickfont=dict(color="#9AC89E")),
            margin=dict(t=40, b=20, l=10, r=60),
            height=300,
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.markdown(kpi_card("Leads by Channel", "No lead data yet", muted=True), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── CPL Cards ─────────────────────────────────────────────────────────────────
st.markdown('<h3 style="color:#9AC89E;font-size:1rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem;">Cost Per Lead by Channel</h3>',
            unsafe_allow_html=True)
cpl1, cpl2, cpl3 = st.columns(3)

# Google Ads — not connected
cpl1.markdown(cpl_card("Google Ads CPL", "—", connected=False), unsafe_allow_html=True)

# LinkedIn CPL
if li_ok and li_leads > 0 and li_spend > 0:
    li_cpl = li_spend / li_leads
    cpl2.markdown(cpl_card("LinkedIn CPL", fmt_currency(li_cpl)), unsafe_allow_html=True)
elif li_ok:
    cpl2.markdown(cpl_card("LinkedIn CPL", "No leads tracked", muted=True), unsafe_allow_html=True)
else:
    cpl2.markdown(cpl_card("LinkedIn CPL", "—", connected=False), unsafe_allow_html=True)

# Facebook CPL
if meta_ok and fb_leads > 0 and fb_spend > 0:
    fb_cpl = fb_spend / fb_leads
    cpl3.markdown(cpl_card("Facebook CPL", fmt_currency(fb_cpl)), unsafe_allow_html=True)
elif meta_ok:
    cpl3.markdown(cpl_card("Facebook CPL", "No leads tracked", muted=True), unsafe_allow_html=True)
else:
    cpl3.markdown(cpl_card("Facebook CPL", "—", connected=False), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Organic Search summary ────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<h3 style="color:#9AC89E;font-size:1rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem;">Organic Search (Google Search Console)</h3>',
            unsafe_allow_html=True)
if gsc_ok and gsc_data:
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.markdown(kpi_card("Clicks",      fmt_number(gsc_data["clicks"])),     unsafe_allow_html=True)
    sc2.markdown(kpi_card("Impressions", fmt_number(gsc_data["impressions"])), unsafe_allow_html=True)
    sc3.markdown(kpi_card("Avg CTR",     fmt_pct(gsc_data["ctr"])),           unsafe_allow_html=True)
    sc4.markdown(kpi_card("Avg Position", f'{gsc_data["position"]:.1f}'),     unsafe_allow_html=True)
else:
    st.info(f"Search Console not connected. {gsc_err[:100] if gsc_err else ''}", icon="ℹ️")

st.markdown("---")
st.caption(f"Dashboard refreshes hourly · Data as of {datetime.now().strftime('%b %d, %Y %I:%M %p')}")
