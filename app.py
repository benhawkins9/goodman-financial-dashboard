import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils.sidebar import render_sidebar

st.set_page_config(
    page_title="Goodman Financial — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main,.block-container{background-color:#F8F9FA!important;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] span{color:#1A1A2E!important;}
.stCaption,[data-testid="stCaptionContainer"]{color:#6B7280!important;}
label{color:#6B7280!important;}
h1{color:#1A1A2E!important;font-weight:700;}h2{color:#1A1A2E!important;font-weight:600;}h3,h4{color:#0F6E56!important;font-weight:600;}
[data-testid="stSidebar"]{background-color:#1C2B2B!important;}
[data-testid="stSidebar"] *{color:#E8F0EF!important;}
[data-testid="stSidebarNav"] a:hover{background-color:rgba(255,255,255,0.10)!important;}
[data-testid="stSidebarNav"] a[aria-selected="true"]{background-color:#0F6E56!important;border-left:3px solid #1A9E7A;}
.stButton>button[kind="primary"]{background-color:#0F6E56!important;border-color:#0F6E56!important;color:#FFFFFF!important;font-weight:600;border-radius:6px;}
.stButton>button[kind="primary"]:hover{background-color:#0C5A45!important;border-color:#0C5A45!important;}
.stButton>button:not([kind="primary"]){background-color:#FFFFFF!important;border-color:#E2E8E4!important;color:#1A1A2E!important;border-radius:6px;}
.stTabs [data-baseweb="tab-list"]{background-color:transparent;border-bottom:2px solid #E2E8E4;}
.stTabs [data-baseweb="tab"]{color:#6B7280!important;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{border-bottom:3px solid #0F6E56!important;color:#1A1A2E!important;font-weight:600;}
[data-testid="stDataFrame"]{border:1px solid #E2E8E4;border-radius:8px;}
[data-testid="stAlert"]{background-color:#F0F7F4!important;border-color:#E2E8E4!important;}
hr{border-color:#E2E8E4!important;}
</style>
"""
st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def kpi_card(title, value, delta=None, muted=False):
    val_color = "#6B7280" if muted else "#1A1A2E"
    delta_html = ""
    if delta is not None:
        clr   = "#0F6E56" if delta >= 0 else "#C0392B"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<p style="color:{clr};font-size:12px;margin:4px 0 0;">{arrow} {abs(delta):.1f}%</p>'
    return f"""<div style="background:#FFFFFF;border:1px solid #E2E8E4;border-left:4px solid #0F6E56;
                border-radius:8px;padding:1.1rem 1.25rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);height:100%;">
        <p style="color:#6B7280;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px;">{title}</p>
        <h2 style="color:{val_color};font-size:28px;font-weight:600;margin:0;">{value}</h2>
        {delta_html}</div>"""

def cpl_card(title, value, connected=True, muted=False):
    border = "#0F6E56" if (connected and not muted) else "#E2E8E4"
    vc     = "#6B7280" if (muted or not connected) else "#1A1A2E"
    sub    = "" if connected else '<p style="color:#6B7280;font-size:12px;margin:4px 0 0;">Not connected</p>'
    return f"""<div style="background:#FFFFFF;border:1px solid #E2E8E4;border-left:4px solid {border};
                border-radius:8px;padding:1.1rem 1.25rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);height:100%;">
        <p style="color:#6B7280;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px;">{title}</p>
        <h2 style="color:{vc};font-size:28px;font-weight:600;margin:0;">{value}</h2>{sub}</div>"""

def source_badge(label, connected):
    if connected:
        return f'<span style="background:#F0F7F4;color:#0F6E56;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;border:1px solid #B8DFCF;">✓ {label}</span>'
    return f'<span style="background:#FDF2F2;color:#C0392B;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;border:1px solid #F1C0C0;">✗ {label}</span>'

def fmt_number(n):
    if n is None: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return f"{int(n):,}"

def fmt_currency(n):
    return f"${n:,.2f}" if n is not None else "—"

def fmt_pct(n):
    return f"{n:.2f}%" if n is not None else "—"

def pct_delta(curr, prev):
    if prev is None or prev == 0 or curr is None: return None
    return ((curr - prev) / abs(prev)) * 100

CHART_BG = "#FFFFFF"
COLORS   = ["#0F6E56", "#1A9E7A", "#5BB89A", "#8ECFC0", "#3D8B70", "#2A6B55"]

def chart_base(title=""):
    return dict(
        title=dict(text=title, font=dict(size=14, color="#1A1A2E"), x=0),
        plot_bgcolor="#FAFAFA", paper_bgcolor="#FFFFFF",
        font=dict(color="#1A1A2E"),
        xaxis=dict(gridcolor="#F0F0F0", linecolor="#E2E8E4", color="#6B7280", tickfont=dict(color="#6B7280")),
        yaxis=dict(gridcolor="#F0F0F0", linecolor="#E2E8E4", color="#6B7280", tickfont=dict(color="#6B7280")),
        margin=dict(t=40, b=20, l=10, r=60),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#1A1A2E")),
    )

# ── Auth ──────────────────────────────────────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center;padding:3rem 0 1.5rem;">
            <div style="width:64px;height:64px;background:#0F6E56;border-radius:12px;
                        display:inline-flex;align-items:center;justify-content:center;
                        font-size:2rem;margin-bottom:1rem;">📊</div>
            <h1 style="color:#1A1A2E;margin:0;font-size:1.8rem;">Goodman Financial</h1>
            <p style="color:#6B7280;margin:0.4rem 0 2rem;">Marketing Analytics Dashboard</p>
        </div>""", unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="collapsed")
        if st.button("Sign In", use_container_width=True, type="primary"):
            if pwd == st.secrets.get("APP_PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password — please try again.")
        st.markdown('<p style="text-align:center;color:#6B7280;font-size:0.75rem;margin-top:2rem;">© 2025 Goodman Financial</p>', unsafe_allow_html=True)
    return False

if not check_password():
    st.stop()

dates = render_sidebar()
start_date, end_date       = dates["start_date"], dates["end_date"]
start_str, end_str         = dates["start_str"],  dates["end_str"]
compare_enabled            = dates["compare_enabled"]
prior_start_str            = dates["prior_start_str"]
prior_end_str              = dates["prior_end_str"]
prior_start, prior_end     = dates["prior_start"], dates["prior_end"]

# ── Fetch functions ───────────────────────────────────────────────────────────
def _build_creds_dict():
    return {
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

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ga4_summary(start, end):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric, OrderBy
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(
        _build_creds_dict(), scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{st.secrets['GA4_PROPERTY_ID']}"

    tot = client.run_report(RunReportRequest(
        property=prop, date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers"), Metric(name="screenPageViews")],
    ))
    row = tot.rows[0].metric_values if tot.rows else None

    ch = client.run_report(RunReportRequest(
        property=prop, date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=8,
    ))
    channels = [{"channel": r.dimension_values[0].value, "sessions": int(r.metric_values[0].value)}
                for r in ch.rows]
    return {
        "sessions":  int(row[0].value) if row else 0,
        "users":     int(row[1].value) if row else 0,
        "pageviews": int(row[2].value) if row else 0,
        "channels":  channels,
    }

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_gsc_summary(start, end):
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(
        _build_creds_dict(), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    svc = build("searchconsole", "v1", credentials=creds)
    res = svc.searchanalytics().query(
        siteUrl=st.secrets["GSC_SITE_URL"],
        body={"startDate": start, "endDate": end, "dimensions": []},
    ).execute()
    row = res.get("rows", [{}])[0]
    return {"clicks": int(row.get("clicks",0)), "impressions": int(row.get("impressions",0)),
            "ctr": row.get("ctr",0)*100, "position": row.get("position",0)}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_meta_summary(start, end):
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    FacebookAdsApi.init(access_token=st.secrets["META_ACCESS_TOKEN"].strip())
    account = AdAccount(st.secrets["META_AD_ACCOUNT_ID"].strip())
    rows = list(account.get_insights(
        fields=["spend","impressions","clicks","ctr","cpc","actions"],
        params={"time_range":{"since":start,"until":end},"level":"account"},
    ))
    row = dict(rows[0]) if rows else {}
    actions = row.get("actions",[])
    leads = sum(int(a.get("value",0)) for a in actions
                if a.get("action_type") in ("lead","offsite_conversion.fb_pixel_lead",
                                            "offsite_conversion.fb_pixel_purchase","purchase"))
    return {"spend": float(row.get("spend",0)), "impressions": int(row.get("impressions",0)),
            "clicks": int(row.get("clicks",0)), "ctr": float(row.get("ctr",0)),
            "cpc": float(row.get("cpc",0)), "leads": leads}

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_linkedin_summary():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_info(
        _build_creds_dict(),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(st.secrets["LINKEDIN_SHEET_ID"]).get_worksheet(0)
    df = pd.DataFrame(ws.get_all_records())
    out = {"rows": len(df)}
    for col in ["Impressions","impressions"]:
        if col in df.columns: out["impressions"] = pd.to_numeric(df[col],errors="coerce").sum(); break
    for col in ["Clicks","clicks","Link Clicks"]:
        if col in df.columns: out["clicks"] = pd.to_numeric(df[col],errors="coerce").sum(); break
    for col in ["Spend","spend","Amount Spent","Cost"]:
        if col in df.columns: out["spend"] = pd.to_numeric(df[col],errors="coerce").sum(); break
    for col in ["Leads","leads","Conversions","conversions","Form Submissions"]:
        if col in df.columns: out["leads"] = pd.to_numeric(df[col],errors="coerce").sum(); break
    return out

# ── Fetch current period ──────────────────────────────────────────────────────
ga4_data, ga4_ok, ga4_err   = None, False, ""
gsc_data, gsc_ok, gsc_err   = None, False, ""
meta_data, meta_ok, meta_err = None, False, ""
li_data,  li_ok,  li_err    = None, False, ""

with st.spinner("Loading data from all channels…"):
    try: ga4_data  = fetch_ga4_summary(start_str, end_str);  ga4_ok  = True
    except Exception as e: ga4_err  = str(e)
    try: gsc_data  = fetch_gsc_summary(start_str, end_str);  gsc_ok  = True
    except Exception as e: gsc_err  = str(e)
    try: meta_data = fetch_meta_summary(start_str, end_str); meta_ok = True
    except Exception as e: meta_err = str(e)
    try: li_data   = fetch_linkedin_summary();               li_ok   = True
    except Exception as e: li_err   = str(e)

# ── Fetch prior period ────────────────────────────────────────────────────────
p_ga4 = p_gsc = p_meta = p_li = None
if compare_enabled and prior_start_str:
    with st.spinner("Loading prior period…"):
        try: p_ga4  = fetch_ga4_summary(prior_start_str, prior_end_str)
        except: pass
        try: p_gsc  = fetch_gsc_summary(prior_start_str, prior_end_str)
        except: pass
        try: p_meta = fetch_meta_summary(prior_start_str, prior_end_str)
        except: pass
        try: p_li   = fetch_linkedin_summary()
        except: pass

# ── Page ─────────────────────────────────────────────────────────────────────
st.markdown("# Goodman Financial — Channel Performance")
st.markdown(
    f'<p style="color:#6B7280;margin-top:-0.5rem;">'
    f'{start_date.strftime("%B %d")} – {end_date.strftime("%B %d, %Y")}'
    + (f' &nbsp;·&nbsp; vs. {prior_start.strftime("%b %d")} – {prior_end.strftime("%b %d, %Y")}' if compare_enabled and prior_start else "")
    + "</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

badges = " &nbsp; ".join([
    source_badge("GA4", ga4_ok), source_badge("Search Console", gsc_ok),
    source_badge("Google Ads", False), source_badge("Facebook Ads", meta_ok),
    source_badge("LinkedIn", li_ok),
])
st.markdown(badges, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Aggregate metrics ─────────────────────────────────────────────────────────
total_sessions = ga4_data["sessions"] if ga4_ok and ga4_data else None
fb_spend = meta_data["spend"]   if meta_ok and meta_data else 0.0
fb_leads = meta_data["leads"]   if meta_ok and meta_data else 0
li_spend = float(li_data.get("spend",0)) if li_ok and li_data else 0.0
li_leads = int(li_data.get("leads",0))   if li_ok and li_data else 0
total_spend = fb_spend + li_spend
total_leads = fb_leads + li_leads
blended_cpl = (total_spend / total_leads) if total_leads > 0 else None

# Prior deltas
d_sessions = pct_delta(total_sessions, p_ga4["sessions"]) if compare_enabled and p_ga4 else None
p_fb_spend = float(p_meta.get("spend",0)) if compare_enabled and p_meta else 0.0
p_li_spend = float(p_li.get("spend",0))   if compare_enabled and p_li  else 0.0
p_total_spend = p_fb_spend + p_li_spend
p_fb_leads = int(p_meta.get("leads",0))   if compare_enabled and p_meta else 0
p_li_leads = int(p_li.get("leads",0))     if compare_enabled and p_li  else 0
p_total_leads = p_fb_leads + p_li_leads
p_cpl = (p_total_spend / p_total_leads) if compare_enabled and p_total_leads > 0 else None

d_spend  = pct_delta(total_spend, p_total_spend)  if compare_enabled else None
d_leads  = pct_delta(total_leads, p_total_leads)  if compare_enabled else None
d_cpl    = pct_delta(blended_cpl, p_cpl)          if compare_enabled else None

# ── 4 KPI cards ──────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_card("Total Sessions", fmt_number(total_sessions) if total_sessions is not None else "—",
                     delta=d_sessions, muted=not ga4_ok), unsafe_allow_html=True)
c2.markdown(kpi_card("Total Leads", fmt_number(total_leads) if (meta_ok or li_ok) else "—",
                     delta=d_leads, muted=not(meta_ok or li_ok)), unsafe_allow_html=True)
c3.markdown(kpi_card("Total Ad Spend", fmt_currency(total_spend) if (meta_ok or li_ok) else "—",
                     delta=d_spend, muted=not(meta_ok or li_ok)), unsafe_allow_html=True)
c4.markdown(kpi_card("Blended CPL", fmt_currency(blended_cpl) if blended_cpl else "—",
                     delta=d_cpl, muted=blended_cpl is None), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Bar charts ────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    if ga4_ok and ga4_data and ga4_data.get("channels"):
        ch_df = pd.DataFrame(ga4_data["channels"]).sort_values("sessions")
        fig = go.Figure(go.Bar(
            x=ch_df["sessions"], y=ch_df["channel"], orientation="h",
            marker_color=COLORS[0],
            text=ch_df["sessions"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont=dict(color="#1A1A2E"),
        ))
        fig.update_layout(**chart_base("Sessions by Channel"), height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown(kpi_card("Sessions by Channel", "GA4 not connected", muted=True), unsafe_allow_html=True)

with col_right:
    lead_labels, lead_vals = [], []
    if meta_ok and fb_leads > 0:  lead_labels.append("Facebook Ads"); lead_vals.append(fb_leads)
    if li_ok  and li_leads > 0:   lead_labels.append("LinkedIn");     lead_vals.append(li_leads)
    if lead_labels:
        fig2 = go.Figure(go.Bar(
            x=lead_vals, y=lead_labels, orientation="h",
            marker_color=COLORS[1],
            text=lead_vals, textposition="outside", textfont=dict(color="#1A1A2E"),
        ))
        fig2.update_layout(**chart_base("Leads by Channel"), height=300)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.markdown(kpi_card("Leads by Channel", "No lead data yet", muted=True), unsafe_allow_html=True)

# ── Sessions donut ────────────────────────────────────────────────────────────
if ga4_ok and ga4_data and ga4_data.get("channels"):
    ch_df = pd.DataFrame(ga4_data["channels"])
    fig3 = px.pie(ch_df, values="sessions", names="channel",
                  hole=0.52, color_discrete_sequence=COLORS)
    fig3.update_layout(
        title=dict(text="Sessions by Default Channel Group", font=dict(size=14, color="#1A1A2E"), x=0),
        plot_bgcolor="#FAFAFA", paper_bgcolor="#FFFFFF",
        font=dict(color="#1A1A2E"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#1A1A2E")),
        margin=dict(t=50, b=20, l=20, r=20), height=340,
    )
    fig3.update_traces(textinfo="percent+label", textfont=dict(color="#1A1A2E"))
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── CPL cards ─────────────────────────────────────────────────────────────────
st.markdown('<h3 style="color:#6B7280;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.75rem;">Cost Per Lead by Channel</h3>', unsafe_allow_html=True)
cc1, cc2, cc3 = st.columns(3)
cc1.markdown(cpl_card("Google Ads CPL", "—", connected=False), unsafe_allow_html=True)
if li_ok and li_leads > 0 and li_spend > 0:
    cc2.markdown(cpl_card("LinkedIn CPL", fmt_currency(li_spend/li_leads)), unsafe_allow_html=True)
elif li_ok:
    cc2.markdown(cpl_card("LinkedIn CPL", "No leads tracked", connected=False), unsafe_allow_html=True)
else:
    cc2.markdown(cpl_card("LinkedIn CPL", "—", connected=False), unsafe_allow_html=True)
if meta_ok and fb_leads > 0 and fb_spend > 0:
    cc3.markdown(cpl_card("Facebook CPL", fmt_currency(fb_spend/fb_leads)), unsafe_allow_html=True)
elif meta_ok:
    cc3.markdown(cpl_card("Facebook CPL", "No leads tracked", connected=False), unsafe_allow_html=True)
else:
    cc3.markdown(cpl_card("Facebook CPL", "—", connected=False), unsafe_allow_html=True)

# ── Organic Search summary ────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<h3 style="color:#6B7280;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.75rem;">Organic Search (Google Search Console)</h3>', unsafe_allow_html=True)
if gsc_ok and gsc_data:
    d_clicks = pct_delta(gsc_data["clicks"], p_gsc["clicks"]) if compare_enabled and p_gsc else None
    d_impr   = pct_delta(gsc_data["impressions"], p_gsc["impressions"]) if compare_enabled and p_gsc else None
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.markdown(kpi_card("Clicks",       fmt_number(gsc_data["clicks"]),      delta=d_clicks), unsafe_allow_html=True)
    sc2.markdown(kpi_card("Impressions",  fmt_number(gsc_data["impressions"]), delta=d_impr),   unsafe_allow_html=True)
    sc3.markdown(kpi_card("Avg CTR",      fmt_pct(gsc_data["ctr"])),                           unsafe_allow_html=True)
    sc4.markdown(kpi_card("Avg Position", f'{gsc_data["position"]:.1f}'),                      unsafe_allow_html=True)
else:
    st.info(f"Search Console not connected. {gsc_err[:100] if gsc_err else ''}", icon="ℹ️")

st.markdown("---")
st.caption(f"Dashboard refreshes hourly · Data as of {datetime.now().strftime('%b %d, %Y %I:%M %p')}")
