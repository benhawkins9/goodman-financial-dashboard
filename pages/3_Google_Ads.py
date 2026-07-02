import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.sidebar import render_sidebar
from utils.theme import get_theme, apply_theme_css, kpi_card, chart_layout, pct_delta

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Google Ads — Goodman Financial", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

dates = render_sidebar()
start_date, end_date   = dates["start_date"], dates["end_date"]
start_str,  end_str    = dates["start_str"],  dates["end_str"]
compare_enabled        = dates["compare_enabled"]
prior_start_str        = dates["prior_start_str"]
prior_end_str          = dates["prior_end_str"]

theme  = get_theme()
apply_theme_css(theme)
COLORS = theme["colors"]

_SECRET_KEYS = ("GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
                "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_ADS_CUSTOMER_ID")


def _build_client(developer_token: str, client_id: str, client_secret: str,
                  refresh_token: str, login_customer_id: str):
    from google.ads.googleads.client import GoogleAdsClient
    config = {
        "developer_token": developer_token,
        "client_id":       client_id,
        "client_secret":   client_secret,
        "refresh_token":   refresh_token,
        "use_proto_plus":  True,
    }
    if login_customer_id:
        config["login_customer_id"] = login_customer_id.replace("-", "")
    return GoogleAdsClient.load_from_dict(config)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_google_ads(start: str, end: str, customer_id: str,
                     developer_token: str, client_id: str, client_secret: str,
                     refresh_token: str, login_customer_id: str):
    client  = _build_client(developer_token, client_id, client_secret,
                            refresh_token, login_customer_id)
    service = client.get_service("GoogleAdsService")
    cid     = customer_id.replace("-", "")

    def search(query: str):
        rows = []
        for batch in service.search_stream(customer_id=cid, query=query):
            rows.extend(batch.results)
        return rows

    date_clause = f"segments.date BETWEEN '{start}' AND '{end}'"

    totals_rows = search(f"""
        SELECT metrics.cost_micros, metrics.impressions, metrics.clicks,
               metrics.ctr, metrics.average_cpc, metrics.conversions,
               metrics.cost_per_conversion
        FROM customer WHERE {date_clause}""")
    t = totals_rows[0].metrics if totals_rows else None

    daily = [
        {"date":        r.segments.date,
         "spend":       r.metrics.cost_micros / 1e6,
         "impressions": int(r.metrics.impressions),
         "clicks":      int(r.metrics.clicks),
         "conversions": float(r.metrics.conversions)}
        for r in search(f"""
            SELECT segments.date, metrics.cost_micros, metrics.impressions,
                   metrics.clicks, metrics.conversions
            FROM customer WHERE {date_clause}
            ORDER BY segments.date""")
    ]

    campaigns = [
        {"campaign":    r.campaign.name,
         "status":      r.campaign.status.name.title(),
         "spend":       r.metrics.cost_micros / 1e6,
         "impressions": int(r.metrics.impressions),
         "clicks":      int(r.metrics.clicks),
         "ctr":         r.metrics.ctr * 100,
         "cpc":         r.metrics.average_cpc / 1e6,
         "conversions": float(r.metrics.conversions)}
        for r in search(f"""
            SELECT campaign.name, campaign.status, metrics.cost_micros,
                   metrics.impressions, metrics.clicks, metrics.ctr,
                   metrics.average_cpc, metrics.conversions
            FROM campaign WHERE {date_clause} AND metrics.impressions > 0
            ORDER BY metrics.cost_micros DESC LIMIT 20""")
    ]

    keywords = [
        {"keyword":     r.ad_group_criterion.keyword.text,
         "match_type":  r.ad_group_criterion.keyword.match_type.name.title(),
         "spend":       r.metrics.cost_micros / 1e6,
         "impressions": int(r.metrics.impressions),
         "clicks":      int(r.metrics.clicks),
         "ctr":         r.metrics.ctr * 100,
         "cpc":         r.metrics.average_cpc / 1e6,
         "conversions": float(r.metrics.conversions)}
        for r in search(f"""
            SELECT ad_group_criterion.keyword.text,
                   ad_group_criterion.keyword.match_type,
                   metrics.cost_micros, metrics.impressions, metrics.clicks,
                   metrics.ctr, metrics.average_cpc, metrics.conversions
            FROM keyword_view WHERE {date_clause} AND metrics.impressions > 0
            ORDER BY metrics.cost_micros DESC LIMIT 25""")
    ]

    return {
        "spend":         t.cost_micros / 1e6 if t else 0.0,
        "impressions":   int(t.impressions)  if t else 0,
        "clicks":        int(t.clicks)       if t else 0,
        "ctr":           t.ctr * 100         if t else 0.0,
        "cpc":           t.average_cpc / 1e6 if t else 0.0,
        "conversions":   float(t.conversions) if t else 0.0,
        "cost_per_conv": t.cost_per_conversion / 1e6 if t else 0.0,
        "daily": daily, "campaigns": campaigns, "keywords": keywords,
    }


def render_setup_card():
    st.markdown(f"""
<div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-left:5px solid #D4A017;
            border-radius:10px;padding:2rem 2.5rem;max-width:720px;margin:2rem auto;
            box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <span style="font-size:1.8rem;">🔑</span>
        <h2 style="color:{theme['text_primary']};margin:0;font-size:1.3rem;font-weight:700;">Google Ads Credentials Pending</h2>
    </div>
    <p style="color:{theme['text_primary']};margin:0 0 1rem;line-height:1.6;">
        This page is fully built and will display campaign data as soon as credentials are added to
        <code style="background:{theme['bg']};padding:1px 5px;border-radius:3px;color:{theme['accent']};border:1px solid {theme['card_border']};">secrets.toml</code>.
    </p>
    <hr style="border-color:{theme['card_border']};margin:1.25rem 0;">
    <h3 style="color:{theme['accent']};font-size:1rem;margin:0 0 0.75rem;">Steps to connect Google Ads</h3>
    <ol style="color:{theme['text_primary']};line-height:1.9;margin:0;padding-left:1.3rem;">
        <li><strong style="color:{theme['accent']};">Developer token</strong> — Apply in your Google Ads Manager Account under
            <em>Tools &amp; Settings → API Center</em>.</li>
        <li><strong style="color:{theme['accent']};">OAuth 2.0 credentials</strong> — Create a <em>Desktop app</em> OAuth client
            in Google Cloud Console (APIs &amp; Services → Credentials). Enable the <em>Google Ads API</em> for the project.</li>
        <li><strong style="color:{theme['accent']};">Refresh token</strong> — Run
            <code style="color:{theme['accent']};">python generate_refresh_token.py</code> (in this repo) on your computer,
            sign in with a Google account that can access the ad account, and copy the printed token.</li>
        <li><strong style="color:{theme['accent']};">Customer ID</strong> — Found in the top-right of the Google Ads UI (format: 123-456-7890).</li>
        <li><strong style="color:{theme['accent']};">Add to secrets.toml</strong> — Add the <code style="color:{theme['accent']};">GOOGLE_ADS_*</code> keys below.</li>
    </ol>
    <hr style="border-color:{theme['card_border']};margin:1.25rem 0;">
    <pre style="background:{theme['bg']};border:1px solid {theme['card_border']};border-radius:6px;padding:1rem;
                font-size:0.85rem;color:{theme['accent']};overflow-x:auto;margin:0;">
GOOGLE_ADS_DEVELOPER_TOKEN   = "your-developer-token"
GOOGLE_ADS_CLIENT_ID         = "000000000000-xxxxx.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET     = "GOCSPX-xxxxxxxxxxxxxxxxxxxx"
GOOGLE_ADS_REFRESH_TOKEN     = "1//0xxxxxxxxxxxxxxxxxxxxxxxx"
GOOGLE_ADS_CUSTOMER_ID       = "123-456-7890"
# Only if access is via a Manager (MCC) account:
# GOOGLE_ADS_LOGIN_CUSTOMER_ID = "123-456-7890"</pre>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### What you'll see once connected")
    preview_cols = st.columns(5)
    for col, label in zip(preview_cols, ["Spend", "Impressions", "Clicks", "CTR", "Conversions"]):
        col.markdown(f"""
        <div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-left:4px solid {theme['card_border']};
                    border-radius:8px;padding:1.1rem 1.25rem;opacity:0.5;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <p style="color:{theme['text_secondary']};font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px;">{label}</p>
            <h2 style="color:{theme['card_border']};font-size:28px;font-weight:600;margin:0;">—</h2>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Google Ads · Credentials not yet configured")


# ── Page ─────────────────────────────────────────────────────────────────────
st.markdown("## Google Ads")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

missing = [k for k in _SECRET_KEYS if not st.secrets.get(k, "")]
if missing:
    render_setup_card()
    st.stop()

_creds_args = (
    st.secrets["GOOGLE_ADS_DEVELOPER_TOKEN"].strip(),
    st.secrets["GOOGLE_ADS_CLIENT_ID"].strip(),
    st.secrets["GOOGLE_ADS_CLIENT_SECRET"].strip(),
    st.secrets["GOOGLE_ADS_REFRESH_TOKEN"].strip(),
    str(st.secrets.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")).strip(),
)
customer_id = str(st.secrets["GOOGLE_ADS_CUSTOMER_ID"]).strip()

with st.spinner("Fetching Google Ads data…"):
    try:
        data = fetch_google_ads(start_str, end_str, customer_id, *_creds_args)
    except Exception as e:
        st.error(f"Could not load Google Ads data: {e}")
        st.code(str(e), language="text")
        st.markdown("**Checklist:**\n"
                    "- Developer token must be approved (Basic access is enough for your own accounts)\n"
                    "- The Google account used for the refresh token must have access to this customer ID\n"
                    "- If access is through a Manager (MCC) account, set `GOOGLE_ADS_LOGIN_CUSTOMER_ID`\n"
                    "- `GOOGLE_ADS_CUSTOMER_ID` is the account being reported on (dashes optional)")
        st.stop()

prior_data = None
if compare_enabled and prior_start_str and prior_end_str:
    with st.spinner("Fetching comparison period…"):
        try:
            prior_data = fetch_google_ads(prior_start_str, prior_end_str, customer_id, *_creds_args)
        except Exception:
            prior_data = None

# ── Empty state ───────────────────────────────────────────────────────────────
has_data = data["spend"] > 0 or data["impressions"] > 0
if not has_data:
    st.info("No campaign data found for this date range. This may be because the account is new "
            "or has no active campaigns in this period.", icon="ℹ️")
    st.markdown("---")
    st.caption(f"Google Ads API · Account {customer_id} · No data for selected range")
    st.stop()

# ── KPI Cards ────────────────────────────────────────────────────────────────
p = prior_data
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.markdown(kpi_card("Spend",        f"${data['spend']:,.2f}",        pct_delta(data['spend'],       p['spend']       if p else None)), unsafe_allow_html=True)
c2.markdown(kpi_card("Impressions",  f"{data['impressions']:,}",      pct_delta(data['impressions'], p['impressions'] if p else None)), unsafe_allow_html=True)
c3.markdown(kpi_card("Clicks",       f"{data['clicks']:,}",           pct_delta(data['clicks'],      p['clicks']      if p else None)), unsafe_allow_html=True)
c4.markdown(kpi_card("CTR",          f"{data['ctr']:.2f}%",           pct_delta(data['ctr'],         p['ctr']         if p else None)), unsafe_allow_html=True)
c5.markdown(kpi_card("Avg CPC",      f"${data['cpc']:.2f}",           pct_delta(data['cpc'],         p['cpc']         if p else None), lower_is_better=True), unsafe_allow_html=True)
c6.markdown(kpi_card("Conversions",  f"{data['conversions']:,.1f}",   pct_delta(data['conversions'], p['conversions'] if p else None)), unsafe_allow_html=True)
c7.markdown(kpi_card("Cost / Conv.", f"${data['cost_per_conv']:,.2f}" if data['conversions'] > 0 else "—",
                     pct_delta(data['cost_per_conv'], p['cost_per_conv'] if p and p['conversions'] > 0 else None),
                     lower_is_better=True), unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Daily trend ──────────────────────────────────────────────────────────────
daily_df = pd.DataFrame(data["daily"])
if not daily_df.empty:
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    tab1, tab2 = st.tabs(["Spend Over Time", "Impressions & Clicks"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["spend"], name="Spend ($)",
                                 line=dict(color=COLORS[0], width=2.5),
                                 fill="tozeroy", fillcolor=theme["fill_alpha"],
                                 hovertemplate="$%{y:,.2f}<extra>Spend</extra>"))
        fig.update_layout(**chart_layout("Daily Ad Spend", "Date", "Spend ($)"))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=daily_df["date"], y=daily_df["impressions"],
                              name="Impressions", marker_color=theme["bar_fill"], yaxis="y2"))
        fig2.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["clicks"],
                                  name="Clicks", line=dict(color=COLORS[0], width=2.5)))
        layout_args = chart_layout("Impressions & Clicks", "Date")
        layout_args["yaxis"]  = dict(title="Clicks", gridcolor=theme["chart_grid"],
                                     color=theme["chart_axis"], tickfont=dict(color=theme["chart_axis"]),
                                     title_font=dict(color=theme["chart_axis"]))
        layout_args["yaxis2"] = dict(title="Impressions", overlaying="y", side="right",
                                     gridcolor="rgba(0,0,0,0)", color=theme["chart_axis"],
                                     tickfont=dict(color=theme["chart_axis"]),
                                     title_font=dict(color=theme["chart_axis"]))
        fig2.update_layout(**layout_args)
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Campaign breakdown ────────────────────────────────────────────────────────
campaigns_df = pd.DataFrame(data["campaigns"])
if not campaigns_df.empty:
    col_left, col_right = st.columns(2)

    with col_left:
        top10 = campaigns_df.head(10)
        fig3 = go.Figure(go.Bar(
            x=top10["spend"], y=top10["campaign"].str[:40], orientation="h",
            marker_color=COLORS[0],
            text=top10["spend"].apply(lambda v: f"${v:,.0f}"),
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        layout3 = chart_layout("Campaigns by Spend ($)")
        layout3["yaxis"]["autorange"] = "reversed"
        fig3.update_layout(**layout3, height=420)
        st.plotly_chart(fig3, use_container_width=True)

    with col_right:
        conv_df = campaigns_df[campaigns_df["conversions"] > 0].head(10)
        if not conv_df.empty:
            fig4 = go.Figure(go.Bar(
                x=conv_df["conversions"], y=conv_df["campaign"].str[:40], orientation="h",
                marker_color=COLORS[1],
                text=conv_df["conversions"].apply(lambda v: f"{v:,.1f}"),
                textposition="outside", textfont=dict(color=theme["chart_font"]),
            ))
            layout4 = chart_layout("Campaigns by Conversions")
            layout4["yaxis"]["autorange"] = "reversed"
            fig4.update_layout(**layout4, height=420)
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("#### Campaign Detail")
    disp = campaigns_df.copy()
    disp["spend"]       = disp["spend"].apply(lambda x: f"${x:,.2f}")
    disp["cpc"]         = disp["cpc"].apply(lambda x: f"${x:,.2f}")
    disp["ctr"]         = disp["ctr"].apply(lambda x: f"{x:.2f}%")
    disp["conversions"] = disp["conversions"].apply(lambda x: f"{x:,.1f}")
    disp.columns = ["Campaign","Status","Spend ($)","Impressions","Clicks","CTR (%)","CPC ($)","Conversions"]
    st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

# ── Keyword breakdown ─────────────────────────────────────────────────────────
keywords_df = pd.DataFrame(data["keywords"])
if not keywords_df.empty:
    st.markdown("#### Top Keywords")
    disp_kw = keywords_df.copy()
    disp_kw["spend"]       = disp_kw["spend"].apply(lambda x: f"${x:,.2f}")
    disp_kw["cpc"]         = disp_kw["cpc"].apply(lambda x: f"${x:,.2f}")
    disp_kw["ctr"]         = disp_kw["ctr"].apply(lambda x: f"{x:.2f}%")
    disp_kw["conversions"] = disp_kw["conversions"].apply(lambda x: f"{x:,.1f}")
    disp_kw.columns = ["Keyword","Match Type","Spend ($)","Impressions","Clicks","CTR (%)","CPC ($)","Conversions"]
    st.dataframe(disp_kw, use_container_width=True, hide_index=True, height=400)

st.markdown("---")
st.caption(f"Data source: Google Ads API · Account {customer_id} · Refreshed hourly")
