import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="Facebook Ads — Goodman Financial",
    page_icon="📣",
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
def fetch_meta(start: str, end: str, account_id: str, access_token: str):
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.adsinsights import AdsInsights

    FacebookAdsApi.init(access_token=access_token)
    account = AdAccount(account_id)

    common_fields = [
        AdsInsights.Field.spend,
        AdsInsights.Field.impressions,
        AdsInsights.Field.clicks,
        AdsInsights.Field.ctr,
        AdsInsights.Field.cpc,
        AdsInsights.Field.reach,
        AdsInsights.Field.frequency,
    ]
    time_range = {"since": start, "until": end}

    # Account-level totals
    totals_iter = account.get_insights(
        fields=common_fields,
        params={"time_range": time_range, "level": "account"},
    )
    totals_list = list(totals_iter)
    totals = dict(totals_list[0]) if totals_list else {}

    # Daily spend for trend chart
    daily_iter = account.get_insights(
        fields=[AdsInsights.Field.spend, AdsInsights.Field.impressions, AdsInsights.Field.clicks],
        params={"time_range": time_range, "time_increment": 1, "level": "account"},
    )
    daily_rows = [
        {
            "date": dict(row).get("date_start", ""),
            "spend": float(dict(row).get("spend", 0)),
            "impressions": int(dict(row).get("impressions", 0)),
            "clicks": int(dict(row).get("clicks", 0)),
        }
        for row in daily_iter
    ]

    # Campaign breakdown
    campaign_fields = common_fields + [
        AdsInsights.Field.campaign_name,
        AdsInsights.Field.actions,
    ]
    campaign_iter = account.get_insights(
        fields=campaign_fields,
        params={
            "time_range": time_range,
            "level": "campaign",
            "sort": [{"field": "spend", "direction": "DESCENDING"}],
            "limit": 20,
        },
    )
    campaign_rows = []
    for row in campaign_iter:
        d = dict(row)
        actions = d.get("actions", [])
        conversions = sum(
            int(a.get("value", 0))
            for a in actions
            if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead",
                                        "offsite_conversion.fb_pixel_purchase", "purchase")
        )
        campaign_rows.append({
            "campaign": d.get("campaign_name", "Unknown"),
            "spend": float(d.get("spend", 0)),
            "impressions": int(d.get("impressions", 0)),
            "clicks": int(d.get("clicks", 0)),
            "ctr": float(d.get("ctr", 0)),
            "cpc": float(d.get("cpc", 0)),
            "conversions": conversions,
        })

    # Adset breakdown
    adset_iter = account.get_insights(
        fields=[
            AdsInsights.Field.adset_name,
            AdsInsights.Field.spend,
            AdsInsights.Field.impressions,
            AdsInsights.Field.clicks,
            AdsInsights.Field.ctr,
            AdsInsights.Field.cpc,
        ],
        params={
            "time_range": time_range,
            "level": "adset",
            "sort": [{"field": "spend", "direction": "DESCENDING"}],
            "limit": 20,
        },
    )
    adset_rows = [
        {
            "adset": dict(r).get("adset_name", ""),
            "spend": float(dict(r).get("spend", 0)),
            "impressions": int(dict(r).get("impressions", 0)),
            "clicks": int(dict(r).get("clicks", 0)),
            "ctr": float(dict(r).get("ctr", 0)),
            "cpc": float(dict(r).get("cpc", 0)),
        }
        for r in adset_iter
    ]

    return {
        "spend": float(totals.get("spend", 0)),
        "impressions": int(totals.get("impressions", 0)),
        "clicks": int(totals.get("clicks", 0)),
        "ctr": float(totals.get("ctr", 0)),
        "cpc": float(totals.get("cpc", 0)),
        "reach": int(totals.get("reach", 0)),
        "frequency": float(totals.get("frequency", 0)),
        "daily": daily_rows,
        "campaigns": campaign_rows,
        "adsets": adset_rows,
    }


# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown("## Facebook / Meta Ads")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

try:
    access_token = st.secrets["META_ACCESS_TOKEN"].strip()
    account_id = st.secrets["META_AD_ACCOUNT_ID"].strip()
except KeyError as e:
    st.error(f"Missing secret: {e}. Add META_ACCESS_TOKEN and META_AD_ACCOUNT_ID to secrets.toml.")
    st.stop()

with st.expander("🔍 Debug — credential check (expand to verify)", expanded=False):
    st.markdown(f"**Ad Account ID:** `{account_id}`")
    st.markdown(f"**Access Token (first 10 chars):** `{access_token[:10]}…` &nbsp; length: `{len(access_token)}`")
    if len(access_token) < 50:
        st.warning("Token looks short — it may be truncated in secrets.toml. Tokens are typically 150–250 characters.")

with st.spinner("Fetching Meta Ads data…"):
    try:
        data = fetch_meta(start_str, end_str, account_id, access_token)
    except Exception as e:
        st.error(f"Could not load Meta Ads data: {e}")
        st.markdown("**Full error details:**")
        st.code(str(e), language="text")
        st.markdown("**Checklist:**")
        st.markdown(
            "- Confirm `META_ACCESS_TOKEN` is a **System User** token (not a short-lived user token)\n"
            "- Token must have `ads_read` and `ads_management` permissions\n"
            "- `META_AD_ACCOUNT_ID` must be in the format `act_XXXXXXXXXX`\n"
            "- Token must not be expired — regenerate in Meta Business Manager if needed"
        )
        st.stop()

# ── KPI Cards ──
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.markdown(kpi_card("Spend", f"${data['spend']:,.2f}"), unsafe_allow_html=True)
c2.markdown(kpi_card("Impressions", f"{data['impressions']:,}"), unsafe_allow_html=True)
c3.markdown(kpi_card("Reach", f"{data['reach']:,}"), unsafe_allow_html=True)
c4.markdown(kpi_card("Clicks", f"{data['clicks']:,}"), unsafe_allow_html=True)
c5.markdown(kpi_card("CTR", f"{data['ctr']:.2f}%"), unsafe_allow_html=True)
c6.markdown(kpi_card("CPC", f"${data['cpc']:.2f}"), unsafe_allow_html=True)
c7.markdown(kpi_card("Frequency", f"{data['frequency']:.2f}"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Daily trend ──
daily_df = pd.DataFrame(data["daily"])
if not daily_df.empty:
    daily_df["date"] = pd.to_datetime(daily_df["date"])

    tab1, tab2 = st.tabs(["Spend Over Time", "Impressions & Clicks"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_df["date"], y=daily_df["spend"],
            name="Spend ($)", line=dict(color="#0F6E56", width=2.5),
            fill="tozeroy", fillcolor="rgba(15,110,86,0.08)",
            hovertemplate="$%{y:,.2f}<extra>Spend</extra>",
        ))
        fig.update_layout(**chart_layout("Daily Ad Spend", "Date", "Spend ($)"))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=daily_df["date"], y=daily_df["impressions"],
            name="Impressions", marker_color="rgba(15,110,86,0.2)", yaxis="y2",
        ))
        fig2.add_trace(go.Scatter(
            x=daily_df["date"], y=daily_df["clicks"],
            name="Clicks", line=dict(color="#0F6E56", width=2.5),
        ))
        fig2.update_layout(
            **chart_layout("Impressions & Clicks", "Date"),
            yaxis=dict(title="Clicks", gridcolor="#F3F4F6"),
            yaxis2=dict(title="Impressions", overlaying="y", side="right", gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Campaign breakdown ──
campaigns_df = pd.DataFrame(data["campaigns"])
if not campaigns_df.empty:
    col_left, col_right = st.columns(2)

    with col_left:
        top_campaigns = campaigns_df.head(10)
        fig3 = go.Figure(go.Bar(
            x=top_campaigns["spend"],
            y=top_campaigns["campaign"].str[:40],
            orientation="h",
            marker_color=COLORS[0],
            text=top_campaigns["spend"].apply(lambda v: f"${v:,.0f}"),
            textposition="outside",
        ))
        fig3.update_layout(**chart_layout("Campaigns by Spend ($)"))
        fig3.update_layout(yaxis=dict(autorange="reversed"), height=420)
        st.plotly_chart(fig3, use_container_width=True)

    with col_right:
        if "conversions" in campaigns_df.columns:
            conv_df = campaigns_df[campaigns_df["conversions"] > 0].head(10)
            if not conv_df.empty:
                fig4 = go.Figure(go.Bar(
                    x=conv_df["conversions"],
                    y=conv_df["campaign"].str[:40],
                    orientation="h",
                    marker_color=COLORS[1],
                    text=conv_df["conversions"],
                    textposition="outside",
                ))
                fig4.update_layout(**chart_layout("Campaigns by Conversions"))
                fig4.update_layout(yaxis=dict(autorange="reversed"), height=420)
                st.plotly_chart(fig4, use_container_width=True)

    st.markdown("#### Campaign Detail")
    display_df = campaigns_df.rename(columns={
        "campaign": "Campaign",
        "spend": "Spend ($)",
        "impressions": "Impressions",
        "clicks": "Clicks",
        "ctr": "CTR (%)",
        "cpc": "CPC ($)",
        "conversions": "Conversions",
    })
    display_df["Spend ($)"] = display_df["Spend ($)"].apply(lambda x: f"${x:,.2f}")
    display_df["CPC ($)"] = display_df["CPC ($)"].apply(lambda x: f"${x:,.2f}")
    display_df["CTR (%)"] = display_df["CTR (%)"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Adset breakdown ──
adsets_df = pd.DataFrame(data["adsets"])
if not adsets_df.empty:
    st.markdown("#### Ad Set Detail")
    display_as = adsets_df.rename(columns={
        "adset": "Ad Set",
        "spend": "Spend ($)",
        "impressions": "Impressions",
        "clicks": "Clicks",
        "ctr": "CTR (%)",
        "cpc": "CPC ($)",
    })
    display_as["Spend ($)"] = display_as["Spend ($)"].apply(lambda x: f"${x:,.2f}")
    display_as["CPC ($)"] = display_as["CPC ($)"].apply(lambda x: f"${x:,.2f}")
    display_as["CTR (%)"] = display_as["CTR (%)"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_as, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(f"Data source: Meta Marketing API · Account {account_id} · Refreshed hourly")
