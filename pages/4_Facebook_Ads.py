import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.sidebar import render_sidebar
from utils.theme import get_theme, apply_theme_css, kpi_card, chart_layout, pct_delta

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Facebook Ads — Goodman Financial", page_icon="📣",
                   layout="wide", initial_sidebar_state="expanded")

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

dates = render_sidebar()
start_date, end_date   = dates["start_date"], dates["end_date"]
compare_enabled        = dates["compare_enabled"]
prior_start_str        = dates["prior_start_str"]
prior_end_str          = dates["prior_end_str"]

theme  = get_theme()
apply_theme_css(theme)
COLORS = theme["colors"]


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_meta(start: str, end: str, account_id: str, access_token: str):
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.adsinsights import AdsInsights

    FacebookAdsApi.init(access_token=access_token)
    account = AdAccount(account_id)
    time_range = {"since": start, "until": end}

    common_fields = [AdsInsights.Field.spend, AdsInsights.Field.impressions,
                     AdsInsights.Field.clicks, AdsInsights.Field.ctr,
                     AdsInsights.Field.cpc, AdsInsights.Field.reach, AdsInsights.Field.frequency]

    totals_list = list(account.get_insights(
        fields=common_fields + [AdsInsights.Field.actions],
        params={"time_range": time_range, "level": "account"},
    ))
    totals = dict(totals_list[0]) if totals_list else {}
    actions = totals.get("actions", [])
    leads = sum(int(a.get("value", 0)) for a in actions
                if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead",
                                            "offsite_conversion.fb_pixel_purchase", "purchase"))

    daily_rows = [
        {"date": dict(r).get("date_start",""), "spend": float(dict(r).get("spend",0)),
         "impressions": int(dict(r).get("impressions",0)), "clicks": int(dict(r).get("clicks",0))}
        for r in account.get_insights(
            fields=[AdsInsights.Field.spend, AdsInsights.Field.impressions, AdsInsights.Field.clicks],
            params={"time_range": time_range, "time_increment": 1, "level": "account"},
        )
    ]

    campaign_rows = []
    for row in account.get_insights(
        fields=common_fields + [AdsInsights.Field.campaign_name, AdsInsights.Field.actions],
        params={"time_range": time_range, "level": "campaign",
                "sort": [{"field": "spend", "direction": "DESCENDING"}], "limit": 20},
    ):
        d = dict(row)
        conv = sum(int(a.get("value", 0)) for a in d.get("actions", [])
                   if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead",
                                               "offsite_conversion.fb_pixel_purchase", "purchase"))
        campaign_rows.append({
            "campaign": d.get("campaign_name", "Unknown"),
            "spend": float(d.get("spend", 0)), "impressions": int(d.get("impressions", 0)),
            "clicks": int(d.get("clicks", 0)), "ctr": float(d.get("ctr", 0)),
            "cpc": float(d.get("cpc", 0)), "conversions": conv,
        })

    adset_rows = [
        {"adset": dict(r).get("adset_name",""), "spend": float(dict(r).get("spend",0)),
         "impressions": int(dict(r).get("impressions",0)), "clicks": int(dict(r).get("clicks",0)),
         "ctr": float(dict(r).get("ctr",0)), "cpc": float(dict(r).get("cpc",0))}
        for r in account.get_insights(
            fields=[AdsInsights.Field.adset_name, AdsInsights.Field.spend,
                    AdsInsights.Field.impressions, AdsInsights.Field.clicks,
                    AdsInsights.Field.ctr, AdsInsights.Field.cpc],
            params={"time_range": time_range, "level": "adset",
                    "sort": [{"field": "spend", "direction": "DESCENDING"}], "limit": 20},
        )
    ]

    return {
        "spend": float(totals.get("spend", 0)), "impressions": int(totals.get("impressions", 0)),
        "clicks": int(totals.get("clicks", 0)), "ctr": float(totals.get("ctr", 0)),
        "cpc": float(totals.get("cpc", 0)), "reach": int(totals.get("reach", 0)),
        "frequency": float(totals.get("frequency", 0)), "leads": leads,
        "daily": daily_rows, "campaigns": campaign_rows, "adsets": adset_rows,
    }


# ── Page ─────────────────────────────────────────────────────────────────────
start_str = dates["start_str"]
end_str   = dates["end_str"]

st.markdown("## Facebook / Meta Ads")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

try:
    access_token = st.secrets["META_ACCESS_TOKEN"].strip()
    account_id   = st.secrets["META_AD_ACCOUNT_ID"].strip()
except KeyError as e:
    st.error(f"Missing secret: {e}. Add META_ACCESS_TOKEN and META_AD_ACCOUNT_ID to secrets.toml.")
    st.stop()

with st.expander("🔍 Debug — credential check", expanded=False):
    st.markdown(f"**Ad Account ID:** `{account_id}`")
    st.markdown(f"**Token prefix:** `{access_token[:10]}…` &nbsp; length: `{len(access_token)}`")
    if len(access_token) < 50:
        st.warning("Token looks short — it may be truncated. Tokens are typically 150–250 characters.")

with st.spinner("Fetching Meta Ads data…"):
    try:
        data = fetch_meta(start_str, end_str, account_id, access_token)
    except Exception as e:
        st.error(f"Could not load Meta Ads data: {e}")
        st.code(str(e), language="text")
        st.markdown("**Checklist:**\n"
                    "- `META_ACCESS_TOKEN` must be a **System User** token with `ads_read` permission\n"
                    "- `META_AD_ACCOUNT_ID` must be in the format `act_XXXXXXXXXX`\n"
                    "- Token must not be expired — regenerate in Meta Business Manager if needed")
        st.stop()

prior_data = None
if compare_enabled and prior_start_str and prior_end_str:
    with st.spinner("Fetching comparison period…"):
        try:
            prior_data = fetch_meta(prior_start_str, prior_end_str, account_id, access_token)
        except Exception:
            prior_data = None

# ── Empty state ───────────────────────────────────────────────────────────────
has_data = data["spend"] > 0 or data["impressions"] > 0

if not has_data:
    st.info("No campaign data found for this date range. This may be because the account is new "
            "or has no active campaigns in this period.", icon="ℹ️")
    st.markdown("---")
    st.caption(f"Meta Marketing API · Account {account_id} · No data for selected range")
    st.stop()

# ── KPI Cards ────────────────────────────────────────────────────────────────
p = prior_data
cpl       = data["spend"] / data["leads"] if data["leads"] > 0 else None
prior_cpl = p["spend"] / p["leads"] if p and p["leads"] > 0 else None

c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
c1.markdown(kpi_card("Spend",       f"${data['spend']:,.2f}",   pct_delta(data['spend'],       p['spend']       if p else None)), unsafe_allow_html=True)
c2.markdown(kpi_card("Impressions", f"{data['impressions']:,}", pct_delta(data['impressions'], p['impressions'] if p else None)), unsafe_allow_html=True)
c3.markdown(kpi_card("Reach",       f"{data['reach']:,}",       pct_delta(data['reach'],       p['reach']       if p else None)), unsafe_allow_html=True)
c4.markdown(kpi_card("Clicks",      f"{data['clicks']:,}",      pct_delta(data['clicks'],      p['clicks']      if p else None)), unsafe_allow_html=True)
c5.markdown(kpi_card("CTR",         f"{data['ctr']:.2f}%",      pct_delta(data['ctr'],         p['ctr']         if p else None)), unsafe_allow_html=True)
c6.markdown(kpi_card("CPC",         f"${data['cpc']:.2f}",      pct_delta(data['cpc'],         p['cpc']         if p else None)), unsafe_allow_html=True)
c7.markdown(kpi_card("Leads",       f"{data['leads']:,}",       pct_delta(data['leads'],       p['leads']       if p else None)), unsafe_allow_html=True)
c8.markdown(kpi_card("CPL",         f"${cpl:.2f}" if cpl else "—", pct_delta(cpl, prior_cpl)),                                   unsafe_allow_html=True)
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
                text=conv_df["conversions"],
                textposition="outside", textfont=dict(color=theme["chart_font"]),
            ))
            layout4 = chart_layout("Campaigns by Conversions")
            layout4["yaxis"]["autorange"] = "reversed"
            fig4.update_layout(**layout4, height=420)
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("#### Campaign Detail")
    disp = campaigns_df.copy()
    disp["spend"] = disp["spend"].apply(lambda x: f"${x:,.2f}")
    disp["cpc"]   = disp["cpc"].apply(lambda x: f"${x:,.2f}")
    disp["ctr"]   = disp["ctr"].apply(lambda x: f"{x:.2f}%")
    disp.columns  = ["Campaign","Spend ($)","Impressions","Clicks","CTR (%)","CPC ($)","Conversions"]
    st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

# ── Ad set breakdown ──────────────────────────────────────────────────────────
adsets_df = pd.DataFrame(data["adsets"])
if not adsets_df.empty:
    st.markdown("#### Ad Set Detail")
    disp_as = adsets_df.copy()
    disp_as["spend"] = disp_as["spend"].apply(lambda x: f"${x:,.2f}")
    disp_as["cpc"]   = disp_as["cpc"].apply(lambda x: f"${x:,.2f}")
    disp_as["ctr"]   = disp_as["ctr"].apply(lambda x: f"{x:.2f}%")
    disp_as.columns  = ["Ad Set","Spend ($)","Impressions","Clicks","CTR (%)","CPC ($)"]
    st.dataframe(disp_as, use_container_width=True, hide_index=True, height=400)

st.markdown("---")
st.caption(f"Data source: Meta Marketing API · Account {account_id} · Refreshed hourly")
