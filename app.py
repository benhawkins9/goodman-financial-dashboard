import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils.sidebar import render_sidebar
from utils.theme import (
    get_theme, apply_theme_css, kpi_card, chart_layout,
    pct_delta, fmt_number, fmt_currency, fmt_pct, fmt_duration,
    CHANNEL_COLORS, channel_color,
)

def _rgba(hex_color: str, alpha: float = 0.40) -> str:
    """Convert a #RRGGBB hex color to rgba(r,g,b,alpha)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


st.set_page_config(
    page_title="Goodman Financial — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply theme CSS before any rendering (CSS applies globally regardless of position)
_theme = get_theme()
apply_theme_css(_theme)

st.markdown("""
<style>
[data-testid="stFormSubmitButton"] button {
    background-color: #0F6E56 !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    height: 50px !important;
    width: 100% !important;
    border-radius: 8px !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    background-color: #0A5240 !important;
}
</style>
""", unsafe_allow_html=True)


# ── App-specific helpers (theme-aware closures) ───────────────────────────────
def cpl_card(title, value, connected=True, muted=False):
    t = get_theme()
    border = t["accent"] if (connected and not muted) else t["card_border"]
    vc     = t["text_secondary"] if (muted or not connected) else t["text_primary"]
    sub    = ("" if connected else
              f'<p style="color:{t["text_secondary"]};font-size:12px;margin:4px 0 0;">Not connected</p>')
    return (
        f'<div style="background:{t["card_bg"]};border:1px solid {t["card_border"]};'
        f'border-left:4px solid {border};border-radius:8px;padding:1.1rem 1.25rem;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.08);height:100%;">'
        f'<p style="color:{t["text_secondary"]};font-size:11px;font-weight:500;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px;">{title}</p>'
        f'<h2 style="color:{vc};font-size:28px;font-weight:600;margin:0;">{value}</h2>{sub}</div>'
    )


def source_badge(label, connected):
    dark = st.session_state.get("dark_mode", False)
    if connected:
        if dark:
            return (f'<span style="background:rgba(76,175,80,0.15);color:#4CAF50;'
                    f'padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;'
                    f'border:1px solid rgba(76,175,80,0.40);">✓ {label}</span>')
        return (f'<span style="background:#E8F5E9;color:#0F6E56;'
                f'padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;'
                f'border:1px solid #0F6E56;">✓ {label}</span>')
    if dark:
        return (f'<span style="background:rgba(239,83,80,0.12);color:#EF9A9A;'
                f'padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;'
                f'border:1px solid rgba(239,83,80,0.30);">✗ {label}</span>')
    return (f'<span style="background:#FEF2F2;color:#C0392B;'
            f'padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;'
            f'border:1px solid #C0392B;">✗ {label}</span>')


# ── Auth ──────────────────────────────────────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True
    t = get_theme()
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align:center;padding:3rem 0 1.5rem;">
            <div style="width:64px;height:64px;background:#0F6E56;border-radius:12px;
                        display:inline-flex;align-items:center;justify-content:center;
                        font-size:2rem;margin-bottom:1rem;">📊</div>
            <h1 style="color:{t['text_primary']};margin:0;font-size:1.8rem;">Goodman Financial</h1>
            <p style="color:{t['text_secondary']};margin:0.4rem 0 2rem;">Marketing Analytics Dashboard</p>
        </div>""", unsafe_allow_html=True)
        with st.form("login_form"):
            pwd = st.text_input("Password", type="password", placeholder="Enter your password",
                                label_visibility="collapsed")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
        if submitted:
            if pwd == st.secrets.get("APP_PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password — please try again.")
        st.markdown(f'<p style="text-align:center;color:{t["text_secondary"]};'
                    f'font-size:0.75rem;margin-top:2rem;">© 2025 Goodman Financial</p>',
                    unsafe_allow_html=True)
    return False


if not check_password():
    st.stop()

dates = render_sidebar()
start_date, end_date   = dates["start_date"], dates["end_date"]
start_str,  end_str    = dates["start_str"],  dates["end_str"]
compare_enabled        = dates["compare_enabled"]
prior_start_str        = dates["prior_start_str"]
prior_end_str          = dates["prior_end_str"]
prior_start, prior_end = dates["prior_start"], dates["prior_end"]

# Re-read theme after sidebar renders (dark mode toggle may have changed it)
theme = get_theme()


# ── Fetch helpers ─────────────────────────────────────────────────────────────
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
def fetch_ga4_extended(start, end):
    """Fetch extra overview metrics in one GA4 client session."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric, OrderBy,
        FilterExpression, Filter,
    )
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_info(
        _build_creds_dict(), scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{st.secrets['GA4_PROPERTY_ID']}"

    def run(dimensions, metrics, order_bys=None, limit=20, dim_filter=None):
        kwargs = dict(
            property=prop,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            order_bys=order_bys or [],
            limit=limit,
        )
        if dim_filter:
            kwargs["dimension_filter"] = dim_filter
        return client.run_report(RunReportRequest(**kwargs))

    # 1. Traffic quality totals
    qr = run([], ["sessions", "engagedSessions", "userEngagementDuration", "screenPageViews"])
    qv = qr.rows[0].metric_values if qr.rows else [None] * 4
    sessions_q    = int(qv[0].value) if qv[0] else 0
    engaged_q     = int(qv[1].value) if qv[1] else 0
    eng_dur_q     = float(qv[2].value) if qv[2] else 0.0
    pageviews_q   = int(qv[3].value) if qv[3] else 0
    quality = {
        "engagement_rate":     (engaged_q / sessions_q * 100) if sessions_q > 0 else 0.0,
        "avg_session_duration":(eng_dur_q / sessions_q)       if sessions_q > 0 else 0.0,
        "pages_per_session":   (pageviews_q / sessions_q)     if sessions_q > 0 else 0.0,
    }

    # 2. Daily engagement trend
    dr = run(["date"], ["sessions", "engagedSessions"],
             [OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))], 90)
    engagement_trend = [
        {"date": r.dimension_values[0].value,
         "engagement_rate": (int(r.metric_values[1].value) /
                              max(int(r.metric_values[0].value), 1)) * 100}
        for r in dr.rows
    ]

    # 3. Top converting pages (top 10 by conversions)
    cr = run(["pagePath"], ["sessions", "conversions", "sessionConversionRate"],
             [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="conversions"), desc=True)], 10)
    converting_pages = [
        {"page":            r.dimension_values[0].value,
         "sessions":        int(r.metric_values[0].value),
         "conversions":     int(r.metric_values[1].value),
         "conversion_rate": float(r.metric_values[2].value) * 100}
        for r in cr.rows
        if int(r.metric_values[1].value) > 0
    ]

    # 4. Referral sources (filter: sessionMedium = "referral")
    ref_filter = FilterExpression(filter=Filter(
        field_name="sessionMedium",
        string_filter=Filter.StringFilter(
            value="referral",
            match_type=Filter.StringFilter.MatchType.EXACT,
        )
    ))
    rr = run(["sessionSource"], ["sessions", "engagedSessions"],
             [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
             10, dim_filter=ref_filter)
    referral_sources = [
        {"source":           r.dimension_values[0].value,
         "sessions":         int(r.metric_values[0].value),
         "engaged_sessions": int(r.metric_values[1].value),
         "engagement_rate":  (int(r.metric_values[1].value) /
                               max(int(r.metric_values[0].value), 1)) * 100}
        for r in rr.rows
    ]

    return {
        "quality":          quality,
        "engagement_trend": engagement_trend,
        "converting_pages": converting_pages,
        "referral_sources": referral_sources,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ga4_form_submissions(start, end):
    """Return gform_submission counts by channel and by date.

    Returns a dict with:
      "total"    – int, sum across all channels
      "channels" – list of {"channel": str, "count": int}, sorted desc
      "daily"    – list of {"date": str (YYYYMMDD), "count": int}, sorted asc
    """
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric, OrderBy,
        FilterExpression, Filter,
    )
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(
        _build_creds_dict(), scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{st.secrets['GA4_PROPERTY_ID']}"

    gform_filter = FilterExpression(filter=Filter(
        field_name="eventName",
        string_filter=Filter.StringFilter(
            value="gform_submission",
            match_type=Filter.StringFilter.MatchType.EXACT,
        )
    ))

    # By channel group
    ch_resp = client.run_report(RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=gform_filter,
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
        limit=20,
    ))
    channels = [
        {"channel": r.dimension_values[0].value, "count": int(r.metric_values[0].value)}
        for r in ch_resp.rows
        if int(r.metric_values[0].value) > 0
    ]

    # By date + channel group (for stacked area chart)
    day_resp = client.run_report(RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="date"), Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=gform_filter,
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
        limit=2000,
    ))
    daily_by_channel = [
        {
            "date":    r.dimension_values[0].value,
            "channel": r.dimension_values[1].value,
            "count":   int(r.metric_values[0].value),
        }
        for r in day_resp.rows
    ]

    return {
        "total":            sum(c["count"] for c in channels),
        "channels":         channels,
        "daily_by_channel": daily_by_channel,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ga4_conversion_rate_by_source(start, end):
    """Return top 10 traffic sources by conversion rate (gform_submission / sessions).

    Only sources with >= 10 sessions are included to avoid misleading 100% rates.
    Returns list of dicts: {source, sessions, conversions, conv_rate}.
    """
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric, OrderBy,
        FilterExpression, Filter,
    )
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(
        _build_creds_dict(), scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{st.secrets['GA4_PROPERTY_ID']}"

    # Call 1: sessions by source
    sess_resp = client.run_report(RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=100,
    ))
    sessions_map = {r.dimension_values[0].value: int(r.metric_values[0].value)
                    for r in sess_resp.rows}

    # Call 2: gform_submission events by source
    gform_filter = FilterExpression(filter=Filter(
        field_name="eventName",
        string_filter=Filter.StringFilter(
            value="gform_submission",
            match_type=Filter.StringFilter.MatchType.EXACT,
        )
    ))
    conv_resp = client.run_report(RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=gform_filter,
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
        limit=100,
    ))
    conv_map = {r.dimension_values[0].value: int(r.metric_values[0].value)
                for r in conv_resp.rows}

    rows = []
    for source, sess in sessions_map.items():
        if sess < 10:
            continue
        convs = conv_map.get(source, 0)
        rows.append({
            "source":      source,
            "sessions":    sess,
            "conversions": convs,
            "conv_rate":   convs / sess * 100,
        })
    rows.sort(key=lambda r: -r["conv_rate"])
    return rows[:10]


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_gf_lead_count(start_date, end_date):
    """Return total GF lead count across all configured form IDs."""
    import hmac as _hmac, hashlib, base64, time as _time, json, requests as _req
    api_key     = st.secrets["GF_API_KEY"]
    private_key = st.secrets["GF_PRIVATE_KEY"]
    base        = st.secrets["GF_SITE_URL"].rstrip("/")
    form_ids    = st.secrets["GF_FORM_IDS"].split(",")
    expires     = int(_time.time()) + 3600
    string_to_sign = f"{api_key}:{expires}"
    sig = base64.b64encode(
        _hmac.new(private_key.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    total = 0
    search = json.dumps({"start_date": str(start_date), "end_date": str(end_date)})
    for form_id in form_ids:
        url = (
            f"{base}/gravityformsapi/entries/"
            f"?api_key={api_key}&signature={sig}&expires={expires}"
            f"&form_ids[]={form_id.strip()}"
            f"&paging[page_size]=1&paging[current_page]=1"
            f"&search={search}"
        )
        try:
            data = _req.get(url, timeout=15).json()
            total += int(data.get("response", {}).get("total_count", 0))
        except Exception:
            pass
    return total


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
    return {"clicks": int(row.get("clicks", 0)), "impressions": int(row.get("impressions", 0)),
            "ctr": row.get("ctr", 0) * 100, "position": row.get("position", 0)}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_meta_summary(start, end):
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
    return {"spend": float(row.get("spend", 0)), "impressions": int(row.get("impressions", 0)),
            "clicks": int(row.get("clicks", 0)), "ctr": float(row.get("ctr", 0)),
            "cpc": float(row.get("cpc", 0)), "leads": leads}


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
    for col in ["Impressions", "impressions"]:
        if col in df.columns: out["impressions"] = pd.to_numeric(df[col], errors="coerce").sum(); break
    for col in ["Clicks", "clicks", "Link Clicks"]:
        if col in df.columns: out["clicks"] = pd.to_numeric(df[col], errors="coerce").sum(); break
    for col in ["Spend", "spend", "Amount Spent", "Cost"]:
        if col in df.columns: out["spend"] = pd.to_numeric(df[col], errors="coerce").sum(); break
    for col in ["Leads", "leads", "Conversions", "conversions", "Form Submissions"]:
        if col in df.columns: out["leads"] = pd.to_numeric(df[col], errors="coerce").sum(); break
    return out


# ── Fetch current period ──────────────────────────────────────────────────────
ga4_data, ga4_ok, ga4_err    = None, False, ""
ext_data, ext_ok             = None, False
gsc_data, gsc_ok, gsc_err    = None, False, ""
meta_data, meta_ok, meta_err = None, False, ""
li_data,  li_ok,  li_err     = None, False, ""
form_data                    = {"total": 0, "channels": []}
conv_rate_data               = []
gf_leads, gf_ok              = 0, False

with st.spinner("Loading data from all channels…"):
    try: ga4_data  = fetch_ga4_summary(start_str, end_str);  ga4_ok  = True
    except Exception as e: ga4_err  = str(e)
    try: ext_data  = fetch_ga4_extended(start_str, end_str); ext_ok  = True
    except Exception: pass
    if ga4_ok:
        try: form_data = fetch_ga4_form_submissions(start_str, end_str)
        except Exception: form_data = {"total": 0, "channels": []}
        try: conv_rate_data = fetch_ga4_conversion_rate_by_source(start_str, end_str)
        except Exception: conv_rate_data = []
    try:
        gf_leads = fetch_gf_lead_count(start_date, end_date)
        gf_ok    = True
    except Exception: pass
    try: gsc_data  = fetch_gsc_summary(start_str, end_str);  gsc_ok  = True
    except Exception as e: gsc_err  = str(e)
    try: meta_data = fetch_meta_summary(start_str, end_str); meta_ok = True
    except Exception as e: meta_err = str(e)
    try: li_data   = fetch_linkedin_summary();               li_ok   = True
    except Exception as e: li_err   = str(e)

# ── Fetch prior period ────────────────────────────────────────────────────────
p_ga4 = p_gsc = p_meta = p_li = None
p_ext_data       = None
p_form_data      = {"total": 0, "channels": [], "daily_by_channel": []}
p_conv_rate_data = []
p_gf_leads       = 0
if compare_enabled and prior_start_str:
    with st.spinner("Loading prior period…"):
        try: p_ga4      = fetch_ga4_summary(prior_start_str, prior_end_str)
        except: pass
        try: p_ext_data = fetch_ga4_extended(prior_start_str, prior_end_str)
        except: pass
        try: p_form_data = fetch_ga4_form_submissions(prior_start_str, prior_end_str)
        except: p_form_data = {"total": 0, "channels": [], "daily_by_channel": []}
        try: p_conv_rate_data = fetch_ga4_conversion_rate_by_source(prior_start_str, prior_end_str)
        except: p_conv_rate_data = []
        try: p_gf_leads = fetch_gf_lead_count(prior_start, prior_end)
        except: pass
        try: p_gsc  = fetch_gsc_summary(prior_start_str, prior_end_str)
        except: pass
        try: p_meta = fetch_meta_summary(prior_start_str, prior_end_str)
        except: pass
        try: p_li   = fetch_linkedin_summary()
        except: pass


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("# Goodman Financial — Channel Performance")
st.markdown(
    f'<p style="color:{theme["text_secondary"]};margin-top:-0.5rem;">'
    f'{start_date.strftime("%B %d")} – {end_date.strftime("%B %d, %Y")}'
    + (f' &nbsp;·&nbsp; vs. {prior_start.strftime("%b %d")} – {prior_end.strftime("%b %d, %Y")}'
       if compare_enabled and prior_start else "")
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
li_spend = float(li_data.get("spend", 0)) if li_ok and li_data else 0.0
li_leads = int(li_data.get("leads", 0))   if li_ok and li_data else 0
form_leads         = form_data["total"]
# Use GF API count when available (more accurate than GA4 event count)
organic_leads      = gf_leads if gf_ok else form_leads
total_spend        = fb_spend + li_spend
total_conversions  = fb_leads + li_leads + organic_leads  # paid leads + form submissions
paid_leads         = fb_leads + li_leads                  # for CPL (spend-based)
blended_cpl = (total_spend / paid_leads) if paid_leads > 0 else None

p_fb_spend    = float(p_meta.get("spend", 0)) if compare_enabled and p_meta else 0.0
p_li_spend    = float(p_li.get("spend", 0))   if compare_enabled and p_li  else 0.0
p_total_spend = p_fb_spend + p_li_spend
p_fb_leads    = int(p_meta.get("leads", 0))   if compare_enabled and p_meta else 0
p_li_leads    = int(p_li.get("leads", 0))     if compare_enabled and p_li  else 0
p_paid_leads  = p_fb_leads + p_li_leads
p_organic_leads = p_gf_leads if gf_ok else p_form_data["total"]
p_total_conv  = p_paid_leads + p_organic_leads
p_cpl         = (p_total_spend / p_paid_leads) if compare_enabled and p_paid_leads > 0 else None

d_sessions = pct_delta(total_sessions, p_ga4["sessions"]) if compare_enabled and p_ga4 else None
d_spend    = pct_delta(total_spend, p_total_spend)         if compare_enabled else None
d_conv     = pct_delta(total_conversions, p_total_conv)    if compare_enabled else None
d_cpl      = pct_delta(blended_cpl, p_cpl)                if compare_enabled else None

has_conv = ga4_ok or meta_ok or li_ok or gf_ok


# ── Row 1: 4 main KPI cards ──────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_card("Total Sessions",     fmt_number(total_sessions) if total_sessions is not None else "—",
                     delta=d_sessions, muted=not ga4_ok),              unsafe_allow_html=True)
c2.markdown(kpi_card("Total Conversions",  fmt_number(total_conversions) if has_conv else "—",
                     delta=d_conv, muted=not has_conv),                unsafe_allow_html=True)
c3.markdown(kpi_card("Total Ad Spend",     fmt_currency(total_spend) if (meta_ok or li_ok) else "—",
                     delta=d_spend, muted=not (meta_ok or li_ok)),     unsafe_allow_html=True)
c4.markdown(kpi_card("Blended CPL",        fmt_currency(blended_cpl) if blended_cpl else "—",
                     delta=d_cpl, muted=blended_cpl is None),          unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)


# ── Row 2: Traffic Quality Scorecard ─────────────────────────────────────────
if ext_ok and ext_data:
    q  = ext_data["quality"]
    pq = p_ext_data["quality"] if p_ext_data else None
    st.markdown(f'<p style="color:{theme["text_secondary"]};font-size:11px;font-weight:500;'
                f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">Traffic Quality</p>',
                unsafe_allow_html=True)
    tq1, tq2, tq3, tq4 = st.columns(4)
    tq1.markdown(kpi_card("Engagement Rate",
                           f"{q['engagement_rate']:.1f}%",
                           delta=pct_delta(q['engagement_rate'],       pq['engagement_rate'])       if pq else None),
                 unsafe_allow_html=True)
    tq2.markdown(kpi_card("Avg Session",
                           fmt_duration(q['avg_session_duration']),
                           delta=pct_delta(q['avg_session_duration'],   pq['avg_session_duration'])  if pq else None),
                 unsafe_allow_html=True)
    tq3.markdown(kpi_card("Pages / Session",
                           f"{q['pages_per_session']:.2f}",
                           delta=pct_delta(q['pages_per_session'],      pq['pages_per_session'])     if pq else None),
                 unsafe_allow_html=True)
    # Prefer GF API count; fall back to GA4 event count
    _lead_val   = gf_leads if gf_ok else form_leads
    _p_lead_val = p_gf_leads if gf_ok else p_form_data["total"]
    tq4.markdown(kpi_card("Form Submissions",
                           fmt_number(_lead_val),
                           delta=pct_delta(_lead_val, _p_lead_val) if compare_enabled else None),
                 unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


# ── Row 3: Bar charts ─────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    if ga4_ok and ga4_data and ga4_data.get("channels"):
        cur_ch = ga4_data["channels"]
        cur_map = {r["channel"]: r["sessions"] for r in cur_ch}

        if compare_enabled and p_ga4 and p_ga4.get("channels"):
            pri_map = {r["channel"]: r["sessions"] for r in p_ga4["channels"]}
            # Sort ascending by current sessions so largest appears at top in horizontal bar
            all_ch  = sorted(
                cur_map.keys() | pri_map.keys(),
                key=lambda c: cur_map.get(c, 0),
            )
            cur_vals = [cur_map.get(c, 0) for c in all_ch]
            pri_vals = [pri_map.get(c, 0) for c in all_ch]

            def _delta_label(cur, pri):
                if not pri: return f"{cur:,}"
                pct = (cur - pri) / pri * 100
                arrow = "↑" if pct >= 0 else "↓"
                return f"{cur:,}  {arrow}{abs(pct):.0f}%"

            def _delta_color(cur, pri):
                if not pri: return theme["chart_font"]
                return theme["accent"] if cur >= pri else theme["negative"]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=cur_vals, y=all_ch, orientation="h",
                name="Current",
                marker_color=[channel_color(c) for c in all_ch],
                width=0.6,
                text=[_delta_label(cur_map.get(c, 0), pri_map.get(c, 0)) for c in all_ch],
                textposition="outside",
                textfont=dict(color=[_delta_color(cur_map.get(c, 0), pri_map.get(c, 0)) for c in all_ch]),
            ))
            fig.add_trace(go.Bar(
                x=pri_vals, y=all_ch, orientation="h",
                name="Prior",
                marker_color=[_rgba(channel_color(c), 0.35) for c in all_ch],
                width=0.4,
                text=[f"{v:,}" for v in pri_vals],
                textposition="outside", textfont=dict(color=theme["chart_font"]),
            ))
            layout_ch = chart_layout("Sessions by Channel", compact=True)
            layout_ch["barmode"] = "group"
            fig.update_layout(**layout_ch, height=max(300, len(all_ch) * 80))
        else:
            ch_df = pd.DataFrame(cur_ch).sort_values("sessions")
            fig = go.Figure(go.Bar(
                x=ch_df["sessions"], y=ch_df["channel"], orientation="h",
                marker_color=[channel_color(c) for c in ch_df["channel"]],
                text=ch_df["sessions"].apply(lambda v: f"{v:,}"),
                textposition="outside", textfont=dict(color=theme["chart_font"]),
            ))
            fig.update_layout(**chart_layout("Sessions by Channel", compact=True), height=280)

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown(kpi_card("Sessions by Channel", "GA4 not connected", muted=True),
                    unsafe_allow_html=True)

with col_right:
    form_ch = form_data.get("channels", [])
    if ga4_ok and form_ch:
        # Merge current + prior channels into aligned lists
        all_channels = sorted({r["channel"] for r in form_ch}
                              | {r["channel"] for r in p_form_data.get("channels", [])},
                              key=lambda c: -next((r["count"] for r in form_ch if r["channel"] == c), 0))
        cur_map  = {r["channel"]: r["count"] for r in form_ch}
        pri_map  = {r["channel"]: r["count"] for r in p_form_data.get("channels", [])}
        bar_colors = [channel_color(c) for c in all_channels]

        fig2 = go.Figure()
        def _fs_label(c):
            cur = cur_map.get(c, 0)
            pri = pri_map.get(c, 0) if compare_enabled else 0
            if compare_enabled and pri:
                pct = (cur - pri) / pri * 100
                arrow = "↑" if pct >= 0 else "↓"
                return f"{cur}  {arrow}{abs(pct):.0f}%"
            return str(cur)

        fig2.add_trace(go.Bar(
            x=[cur_map.get(c, 0) for c in all_channels],
            y=all_channels, orientation="h",
            name="Current Period",
            marker_color=bar_colors,
            text=[_fs_label(c) for c in all_channels],
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        if compare_enabled and p_form_data.get("channels"):
            fig2.add_trace(go.Bar(
                x=[pri_map.get(c, 0) for c in all_channels],
                y=all_channels, orientation="h",
                name="Prior Period",
                marker_color=[_rgba(channel_color(c), 0.40) for c in all_channels],
                text=[pri_map.get(c, 0) for c in all_channels],
                textposition="outside", textfont=dict(color=theme["chart_font"]),
            ))
        layout2 = chart_layout("Form Submissions by Channel", compact=True)
        layout2["barmode"] = "group"
        fig2.update_layout(**layout2, height=max(200, len(all_channels) * 52 + 60))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "Note: GA4 may undercount due to ad blockers. "
            "See the **Leads** page for accurate counts."
        )
    else:
        st.markdown(kpi_card("Form Submissions by Channel", "No form data yet", muted=True),
                    unsafe_allow_html=True)


# ── Row 3b: Conversion Rate by Source ────────────────────────────────────────
if ga4_ok and conv_rate_data:
    st.markdown(
        f'<p style="color:{theme["text_secondary"]};font-size:11px;font-weight:500;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin:0.5rem 0 0.75rem;">'
        f'Conversion Rate by Source</p>',
        unsafe_allow_html=True,
    )

    _SOURCE_DEFAULT = "#5BB89A"

    def _source_color(source: str) -> str:
        return CHANNEL_COLORS.get(source, _SOURCE_DEFAULT)

    cur_cr_map = {r["source"]: r for r in conv_rate_data}

    if compare_enabled and p_conv_rate_data:
        pri_cr_map = {r["source"]: r for r in p_conv_rate_data}
        # Union of sources, sorted ascending by current conv_rate so highest is at top
        all_sources = sorted(
            cur_cr_map.keys() | pri_cr_map.keys(),
            key=lambda s: cur_cr_map[s]["conv_rate"] if s in cur_cr_map else 0,
        )
        cur_rates = [cur_cr_map[s]["conv_rate"] if s in cur_cr_map else 0 for s in all_sources]
        pri_rates = [pri_cr_map[s]["conv_rate"] if s in pri_cr_map else 0 for s in all_sources]
        cur_sess  = [cur_cr_map[s]["sessions"]  if s in cur_cr_map else 0 for s in all_sources]
        cur_convs = [cur_cr_map[s]["conversions"] if s in cur_cr_map else 0 for s in all_sources]
        pri_sess  = [pri_cr_map[s]["sessions"]  if s in pri_cr_map else 0 for s in all_sources]
        pri_convs = [pri_cr_map[s]["conversions"] if s in pri_cr_map else 0 for s in all_sources]

        def _cr_delta_color(cur_r, pri_r):
            if not pri_r: return theme["chart_font"]
            return theme["accent"] if cur_r >= pri_r else theme["negative"]

        def _cr_delta_label(cur_r, pri_r):
            if not pri_r: return f"{cur_r:.1f}%"
            pct = (cur_r - pri_r) / pri_r * 100
            arrow = "↑" if pct >= 0 else "↓"
            return f"{cur_r:.1f}%  {arrow}{abs(pct):.0f}%"

        fig_cr = go.Figure()
        fig_cr.add_trace(go.Bar(
            x=cur_rates, y=all_sources, orientation="h",
            name="Current",
            marker_color=[_source_color(s) for s in all_sources],
            width=0.6,
            text=[_cr_delta_label(cur_rates[i], pri_rates[i]) for i in range(len(all_sources))],
            textposition="outside",
            textfont=dict(color=[_cr_delta_color(cur_rates[i], pri_rates[i]) for i in range(len(all_sources))]),
            customdata=list(zip(cur_sess, cur_convs)),
            hovertemplate=(
                "Source: %{y}<br>"
                "Conv Rate: %{x:.2f}%<br>"
                "Sessions: %{customdata[0]:,}<br>"
                "Form Submissions: %{customdata[1]}<extra></extra>"
            ),
        ))
        fig_cr.add_trace(go.Bar(
            x=pri_rates, y=all_sources, orientation="h",
            name="Prior",
            marker_color=[_rgba(_source_color(s), 0.35) for s in all_sources],
            width=0.4,
            text=[f"{r:.1f}%" for r in pri_rates],
            textposition="outside", textfont=dict(color=theme["chart_font"]),
            customdata=list(zip(pri_sess, pri_convs)),
            hovertemplate=(
                "Source: %{y}<br>"
                "Conv Rate: %{x:.2f}%<br>"
                "Sessions: %{customdata[0]:,}<br>"
                "Form Submissions: %{customdata[1]}<extra></extra>"
            ),
        ))
        layout_cr = chart_layout("Conversion Rate by Traffic Source", xaxis_title="Conversion Rate (%)", compact=True)
        layout_cr["barmode"] = "group"
        fig_cr.update_layout(**layout_cr, height=max(300, len(all_sources) * 80))
    else:
        # Single-period version
        sources = [r["source"]      for r in conv_rate_data]
        rates   = [r["conv_rate"]   for r in conv_rate_data]
        sess    = [r["sessions"]    for r in conv_rate_data]
        convs   = [r["conversions"] for r in conv_rate_data]
        # Sort ascending so highest rate is at top
        combined = sorted(zip(sources, rates, sess, convs), key=lambda x: x[1])
        sources, rates, sess, convs = zip(*combined) if combined else ([], [], [], [])

        fig_cr = go.Figure(go.Bar(
            x=list(rates), y=list(sources), orientation="h",
            marker_color=[_source_color(s) for s in sources],
            text=[f"{r:.1f}%" for r in rates],
            textposition="outside", textfont=dict(color=theme["chart_font"]),
            customdata=list(zip(sess, convs)),
            hovertemplate=(
                "Source: %{y}<br>"
                "Conv Rate: %{x:.2f}%<br>"
                "Sessions: %{customdata[0]:,}<br>"
                "Form Submissions: %{customdata[1]}<extra></extra>"
            ),
        ))
        fig_cr.update_layout(
            **chart_layout("Conversion Rate by Traffic Source", xaxis_title="Conversion Rate (%)", compact=True),
            height=max(280, len(sources) * 44 + 60),
        )

    st.plotly_chart(fig_cr, use_container_width=True)
    st.caption("Sources with fewer than 10 sessions excluded")
    st.markdown("<br>", unsafe_allow_html=True)


# ── Row 4: Engagement Rate Trend + Top Converting Pages ──────────────────────
if ext_ok and ext_data:
    col_trend, col_convert = st.columns(2)

    with col_trend:
        et = ext_data.get("engagement_trend", [])
        if et:
            et_df = pd.DataFrame(et)
            et_df["date"] = pd.to_datetime(et_df["date"], format="%Y%m%d")
            fig_et = go.Figure()
            fig_et.add_trace(go.Scatter(
                x=et_df["date"], y=et_df["engagement_rate"],
                name="Engagement Rate (%)",
                line=dict(color=theme["accent"], width=2.5),
                fill="tozeroy", fillcolor=theme["fill_alpha"],
                mode="lines",
            ))
            layout_et = chart_layout("Engagement Rate Trend", "Date", "Engagement Rate (%)")
            fig_et.update_layout(**layout_et, height=280)
            st.plotly_chart(fig_et, use_container_width=True)

    with col_convert:
        cp = ext_data.get("converting_pages", [])
        if cp:
            st.markdown(f'<p style="color:{theme["text_primary"]};font-size:15px;'
                        f'font-weight:600;margin-bottom:0.5rem;">Top Converting Pages</p>',
                        unsafe_allow_html=True)
            cp_df = pd.DataFrame(cp)
            cp_df["conversion_rate"] = cp_df["conversion_rate"].apply(lambda x: f"{x:.2f}%")
            st.dataframe(
                cp_df.rename(columns={
                    "page": "Page", "sessions": "Sessions",
                    "conversions": "Conversions", "conversion_rate": "Conv. Rate"
                }),
                use_container_width=True, hide_index=True, height=280,
            )
        else:
            st.info("No conversion data available. Configure conversion events in GA4.", icon="ℹ️")

    st.markdown("<br>", unsafe_allow_html=True)


# ── Row 4b: Form Submissions Over Time (stacked by channel) ──────────────────
if ga4_ok:
    daily_by_ch = form_data.get("daily_by_channel", [])
    if daily_by_ch:
        raw_df = pd.DataFrame(daily_by_ch)
        raw_df["date"] = pd.to_datetime(raw_df["date"], format="%Y%m%d")

        # Pivot to wide: rows = date, cols = channel
        pivot = raw_df.pivot_table(
            index="date", columns="channel", values="count",
            aggfunc="sum", fill_value=0,
        )

        # Reindex to fill every date in range with 0
        full_range = pd.date_range(start=start_date, end=end_date, freq="D")
        pivot = pivot.reindex(full_range, fill_value=0)
        pivot.index.name = "date"

        # Sort channels by total descending so biggest area is at bottom
        channel_order = pivot.sum().sort_values(ascending=False).index.tolist()
        pivot = pivot[channel_order]

        y_max = int(pivot.sum(axis=1).max()) if not pivot.empty else 1

        fig_fs = go.Figure()
        for i, ch in enumerate(channel_order):
            color = channel_color(ch, fallback_index=i)
            fig_fs.add_trace(go.Scatter(
                x=pivot.index, y=pivot[ch],
                name=ch,
                mode="lines",
                line=dict(color=color, width=1.5),
                fill="tonexty" if i > 0 else "tozeroy",
                fillcolor=_rgba(color, 0.35),
                stackgroup="one",
                hovertemplate=f"<b>{ch}</b><br>%{{x|%b %d}}: %{{y}} submission(s)<extra></extra>",
            ))

        layout_fs = chart_layout(
            "Form Submissions Over Time by Channel", "Date", "Form Submissions"
        )
        layout_fs["yaxis"]["range"] = [0, y_max + 1]
        layout_fs["yaxis"]["dtick"] = 1
        fig_fs.update_layout(**layout_fs, height=300)
        st.plotly_chart(fig_fs, use_container_width=True)
    else:
        st.markdown(
            f'<p style="color:{theme["text_secondary"]};font-size:0.9rem;'
            f'text-align:center;padding:1.5rem 0;">No form submissions recorded in this period</p>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)


# ── Row 5: Sessions donut ─────────────────────────────────────────────────────
if ga4_ok and ga4_data and ga4_data.get("channels"):
    ch_df2 = pd.DataFrame(ga4_data["channels"])
    fig3 = px.pie(ch_df2, values="sessions", names="channel",
                  hole=0.52, color_discrete_sequence=theme["colors"])
    fig3.update_layout(
        title=dict(text="Sessions by Default Channel Group",
                   font=dict(size=14, color=theme["chart_font"]), x=0),
        plot_bgcolor=theme["chart_plot_bg"], paper_bgcolor=theme["chart_bg"],
        font=dict(color=theme["chart_font"]),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=theme["chart_font"])),
        margin=dict(t=50, b=20, l=20, r=20), height=340,
    )
    fig3.update_traces(textinfo="percent+label",
                       textfont=dict(color=theme["chart_font"]))
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Row 6: CPL cards ──────────────────────────────────────────────────────────
st.markdown(
    f'<p style="color:{theme["text_secondary"]};font-size:11px;font-weight:500;'
    f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.75rem;">Cost Per Lead by Channel</p>',
    unsafe_allow_html=True,
)
cc1, cc2, cc3 = st.columns(3)
cc1.markdown(cpl_card("Google Ads CPL", "—", connected=False), unsafe_allow_html=True)
if li_ok and li_leads > 0 and li_spend > 0:
    cc2.markdown(cpl_card("LinkedIn CPL", fmt_currency(li_spend / li_leads)), unsafe_allow_html=True)
elif li_ok:
    cc2.markdown(cpl_card("LinkedIn CPL", "No leads tracked", connected=False), unsafe_allow_html=True)
else:
    cc2.markdown(cpl_card("LinkedIn CPL", "—", connected=False), unsafe_allow_html=True)
if meta_ok and fb_leads > 0 and fb_spend > 0:
    cc3.markdown(cpl_card("Facebook CPL", fmt_currency(fb_spend / fb_leads)), unsafe_allow_html=True)
elif meta_ok:
    cc3.markdown(cpl_card("Facebook CPL", "No leads tracked", connected=False), unsafe_allow_html=True)
else:
    cc3.markdown(cpl_card("Facebook CPL", "—", connected=False), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Row 7: Referral Sources expander ─────────────────────────────────────────
if ext_ok and ext_data and ext_data.get("referral_sources"):
    with st.expander("Referral Sources", expanded=True):
        rs_df = pd.DataFrame(ext_data["referral_sources"])
        rs_df["engagement_rate"] = rs_df["engagement_rate"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(
            rs_df.rename(columns={
                "source": "Source", "sessions": "Sessions",
                "engaged_sessions": "Engaged Sessions", "engagement_rate": "Engagement Rate"
            }),
            use_container_width=True, hide_index=True,
        )


# ── Organic Search summary ────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<p style="color:{theme["text_secondary"]};font-size:11px;font-weight:500;'
    f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.75rem;">'
    f'Organic Search (Google Search Console)</p>',
    unsafe_allow_html=True,
)
if gsc_ok and gsc_data:
    d_clicks = pct_delta(gsc_data["clicks"],       p_gsc["clicks"])       if compare_enabled and p_gsc else None
    d_impr   = pct_delta(gsc_data["impressions"], p_gsc["impressions"]) if compare_enabled and p_gsc else None
    d_ctr    = pct_delta(gsc_data["ctr"],         p_gsc["ctr"])         if compare_enabled and p_gsc else None
    d_pos    = pct_delta(gsc_data["position"],    p_gsc["position"])    if compare_enabled and p_gsc else None
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.markdown(kpi_card("Clicks",       fmt_number(gsc_data["clicks"]),      delta=d_clicks),                    unsafe_allow_html=True)
    sc2.markdown(kpi_card("Impressions",  fmt_number(gsc_data["impressions"]), delta=d_impr),                      unsafe_allow_html=True)
    sc3.markdown(kpi_card("Avg CTR",      fmt_pct(gsc_data["ctr"]),            delta=d_ctr),                       unsafe_allow_html=True)
    sc4.markdown(kpi_card("Avg Position", f'{gsc_data["position"]:.1f}',       delta=d_pos, lower_is_better=True), unsafe_allow_html=True)
else:
    st.info(f"Search Console not connected. {gsc_err[:100] if gsc_err else ''}", icon="ℹ️")

st.markdown("---")
st.caption(f"Dashboard refreshes hourly · Data as of {datetime.now().strftime('%b %d, %Y %I:%M %p')}")
