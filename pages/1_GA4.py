import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.sidebar import render_sidebar
from utils.theme import get_theme, apply_theme_css, kpi_card, chart_layout, pct_delta, fmt_duration

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="GA4 — Goodman Financial", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")

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


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ga4(start: str, end: str, property_id: str,
              project_id: str, private_key_id: str, private_key: str,
              client_email: str, client_id: str, client_x509: str):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric, OrderBy
    from google.oauth2 import service_account

    creds_dict = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": private_key_id,
        "private_key": private_key.replace("\\n", "\n"),
        "client_email": client_email,
        "client_id": client_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": client_x509,
        "universe_domain": "googleapis.com",
    }
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    client = BetaAnalyticsDataClient(credentials=credentials)
    prop = f"properties/{property_id}"

    def run(dimensions, metrics, order_bys=None, limit=50, date_start=start, date_end=end):
        return client.run_report(RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=date_start, end_date=date_end)],
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            order_bys=order_bys or [],
            limit=limit,
        ))

    tot = run([], ["sessions", "activeUsers", "screenPageViews", "bounceRate", "averageSessionDuration"])
    row = tot.rows[0].metric_values if tot.rows else [None] * 5

    daily_resp = run(["date"], ["sessions", "activeUsers"],
                     [OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))])
    daily = [{"date": r.dimension_values[0].value,
               "sessions": int(r.metric_values[0].value),
               "users": int(r.metric_values[1].value)} for r in daily_resp.rows]

    pg_resp = run(["pagePath"], ["screenPageViews", "sessions", "averageSessionDuration"],
                  [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)], 100)
    pages = [{"page": r.dimension_values[0].value,
              "views": int(r.metric_values[0].value),
              "sessions": int(r.metric_values[1].value),
              "avg_duration": float(r.metric_values[2].value)} for r in pg_resp.rows]

    src_resp = run(["sessionDefaultChannelGroup"], ["sessions"],
                   [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)], 10)
    sources = [{"channel": r.dimension_values[0].value,
                "sessions": int(r.metric_values[0].value)} for r in src_resp.rows]

    srcmed_resp = run(["sessionSource", "sessionMedium"], ["sessions", "activeUsers"],
                     [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)], 20)
    source_medium = [{"source": r.dimension_values[0].value,
                      "medium": r.dimension_values[1].value,
                      "sessions": int(r.metric_values[0].value),
                      "users": int(r.metric_values[1].value)} for r in srcmed_resp.rows]

    camp_resp = run(["sessionCampaignName"], ["sessions", "activeUsers", "screenPageViews"],
                    [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)], 20)
    campaigns = [{"campaign": r.dimension_values[0].value,
                  "sessions": int(r.metric_values[0].value),
                  "users": int(r.metric_values[1].value),
                  "pageviews": int(r.metric_values[2].value)} for r in camp_resp.rows]

    evt_resp = run(["eventName"], ["eventCount", "eventCountPerUser"],
                   [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)], 30)
    events = [{"event": r.dimension_values[0].value,
               "count": int(r.metric_values[0].value),
               "per_user": float(r.metric_values[1].value)} for r in evt_resp.rows]

    evt_src_resp = run(["eventName", "sessionDefaultChannelGroup"],
                       ["eventCount"],
                       [OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)], 100)
    events_by_src = [{"event": r.dimension_values[0].value,
                      "channel": r.dimension_values[1].value,
                      "count": int(r.metric_values[0].value)} for r in evt_src_resp.rows]

    return {
        "sessions":     int(row[0].value) if row[0] else 0,
        "users":        int(row[1].value) if row[1] else 0,
        "pageviews":    int(row[2].value) if row[2] else 0,
        "bounce_rate":  float(row[3].value) * 100 if row[3] else 0,
        "avg_duration": float(row[4].value) if row[4] else 0,
        "daily": daily, "pages": pages, "sources": sources,
        "source_medium": source_medium, "campaigns": campaigns,
        "events": events, "events_by_src": events_by_src,
    }


# ── Page ─────────────────────────────────────────────────────────────────────
st.markdown("## Google Analytics 4")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

try:
    property_id      = str(st.secrets["GA4_PROPERTY_ID"])
    _project_id      = st.secrets["GA4_PROJECT_ID"]
    _private_key_id  = st.secrets["GA4_PRIVATE_KEY_ID"]
    _private_key     = st.secrets["GA4_PRIVATE_KEY"]
    _client_email    = st.secrets["GA4_CLIENT_EMAIL"]
    _client_id       = st.secrets["GA4_CLIENT_ID"]
    _client_x509     = st.secrets["GA4_CLIENT_X509_CERT_URL"]
except KeyError as e:
    st.error(f"Missing secret: {e}")
    st.stop()

_creds_args = (_project_id, _private_key_id, _private_key, _client_email, _client_id, _client_x509)

with st.spinner("Fetching GA4 data…"):
    try:
        data = fetch_ga4(start_str, end_str, property_id, *_creds_args)
    except Exception as e:
        st.error(f"Could not load GA4 data: {e}")
        st.stop()

prior_data = None
if compare_enabled and prior_start_str and prior_end_str:
    with st.spinner("Fetching comparison period…"):
        try:
            prior_data = fetch_ga4(prior_start_str, prior_end_str, property_id, *_creds_args)
        except Exception:
            prior_data = None


# ── KPI Cards ────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
kpis = [
    ("Sessions",     f"{data['sessions']:,}",             pct_delta(data['sessions'],     prior_data['sessions']     if prior_data else None)),
    ("Active Users", f"{data['users']:,}",                pct_delta(data['users'],        prior_data['users']        if prior_data else None)),
    ("Page Views",   f"{data['pageviews']:,}",            pct_delta(data['pageviews'],    prior_data['pageviews']    if prior_data else None)),
    ("Bounce Rate",  f"{data['bounce_rate']:.1f}%",       pct_delta(data['bounce_rate'],  prior_data['bounce_rate']  if prior_data else None)),
    ("Avg Session",  fmt_duration(data["avg_duration"]),  pct_delta(data['avg_duration'], prior_data['avg_duration'] if prior_data else None)),
]
for col, (title, val, delta) in zip([c1, c2, c3, c4, c5], kpis):
    col.markdown(kpi_card(title, val, delta), unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)


# ── Daily trend ──────────────────────────────────────────────────────────────
daily_df = pd.DataFrame(data["daily"])
if not daily_df.empty:
    daily_df["date"] = pd.to_datetime(daily_df["date"], format="%Y%m%d")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["sessions"], name="Sessions",
                             line=dict(color=COLORS[0], width=2.5),
                             fill="tozeroy", fillcolor=theme["fill_alpha"]))
    fig.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["users"], name="Active Users",
                             line=dict(color=COLORS[1], width=2, dash="dot")))
    fig.update_layout(**chart_layout("Sessions & Active Users Over Time", "Date", "Count"))
    st.plotly_chart(fig, use_container_width=True)
st.markdown("<br>", unsafe_allow_html=True)


# ── Sessions by channel ───────────────────────────────────────────────────────
sources_df = pd.DataFrame(data["sources"])
if not sources_df.empty:
    col_l, col_r = st.columns(2)
    with col_l:
        fig_bar = go.Figure(go.Bar(
            x=sources_df["sessions"],
            y=sources_df["channel"],
            orientation="h",
            marker_color=COLORS[0],
            text=sources_df["sessions"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        layout_bar = chart_layout("Sessions by Channel")
        layout_bar["yaxis"]["autorange"] = "reversed"
        fig_bar.update_layout(**layout_bar, height=360)
        st.plotly_chart(fig_bar, use_container_width=True)
    with col_r:
        fig_donut = px.pie(sources_df, values="sessions", names="channel",
                           hole=0.52, color_discrete_sequence=COLORS)
        fig_donut.update_layout(**chart_layout("Sessions by Channel"), showlegend=True)
        fig_donut.update_traces(textinfo="percent+label",
                                hovertemplate="%{label}: %{value:,} sessions",
                                textfont=dict(color=theme["chart_font"]))
        st.plotly_chart(fig_donut, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)


# ── Source / Medium ───────────────────────────────────────────────────────────
st.markdown("#### Source / Medium")
srcmed_df = pd.DataFrame(data["source_medium"])
if not srcmed_df.empty:
    srcmed_df["source_medium"] = srcmed_df["source"] + " / " + srcmed_df["medium"]
    top_srcmed = srcmed_df.head(15)
    col_l2, col_r2 = st.columns(2)
    with col_l2:
        fig_sm = go.Figure(go.Bar(
            x=top_srcmed["sessions"],
            y=top_srcmed["source_medium"],
            orientation="h",
            marker_color=COLORS[1],
            text=top_srcmed["sessions"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        layout_sm = chart_layout("Top Source / Medium by Sessions")
        layout_sm["yaxis"]["autorange"] = "reversed"
        fig_sm.update_layout(**layout_sm, height=max(300, len(top_srcmed) * 28))
        st.plotly_chart(fig_sm, use_container_width=True)
    with col_r2:
        fig_sm2 = go.Figure(go.Bar(
            x=top_srcmed["users"],
            y=top_srcmed["source_medium"],
            orientation="h",
            marker_color=COLORS[2],
            text=top_srcmed["users"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        layout_sm2 = chart_layout("Top Source / Medium by Users")
        layout_sm2["yaxis"]["autorange"] = "reversed"
        fig_sm2.update_layout(**layout_sm2, height=max(300, len(top_srcmed) * 28))
        st.plotly_chart(fig_sm2, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)


# ── Campaign Data ─────────────────────────────────────────────────────────────
st.markdown("#### Campaign Performance")
campaigns_df = pd.DataFrame(data["campaigns"])
if not campaigns_df.empty:
    campaigns_df = campaigns_df[campaigns_df["campaign"] != "(not set)"]
if not campaigns_df.empty:
    display_camp = campaigns_df.rename(columns={
        "campaign": "Campaign", "sessions": "Sessions",
        "users": "Users", "pageviews": "Page Views"
    })
    st.dataframe(display_camp, use_container_width=True, hide_index=True, height=300)
else:
    st.info("No campaign data available for this period.")
st.markdown("<br>", unsafe_allow_html=True)


# ── Events Section ────────────────────────────────────────────────────────────
st.markdown("#### Events")
events_df = pd.DataFrame(data["events"])
if not events_df.empty:
    top_events = events_df.head(4)
    ev_cols = st.columns(len(top_events))
    for i, (_, row_ev) in enumerate(top_events.iterrows()):
        ev_cols[i].markdown(kpi_card(row_ev["event"], f"{row_ev['count']:,}"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_ev_l, col_ev_r = st.columns(2)
    with col_ev_l:
        top15_ev = events_df.head(15)
        fig_ev = go.Figure(go.Bar(
            x=top15_ev["count"],
            y=top15_ev["event"],
            orientation="h",
            marker_color=COLORS[0],
            text=top15_ev["count"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        layout_ev = chart_layout("Top Events by Count")
        layout_ev["yaxis"]["autorange"] = "reversed"
        fig_ev.update_layout(**layout_ev, height=max(300, len(top15_ev) * 28))
        st.plotly_chart(fig_ev, use_container_width=True)

    with col_ev_r:
        evs_df = pd.DataFrame(data["events_by_src"])
        if not evs_df.empty:
            top5_events = events_df["event"].head(5).tolist()
            evs_filtered = evs_df[evs_df["event"].isin(top5_events)]
            top_channels = evs_df.groupby("channel")["count"].sum().nlargest(6).index.tolist()
            evs_filtered = evs_filtered[evs_filtered["channel"].isin(top_channels)]
            if not evs_filtered.empty:
                pivot = evs_filtered.pivot_table(index="event", columns="channel",
                                                  values="count", aggfunc="sum", fill_value=0)
                fig_evs = go.Figure()
                for i, ch in enumerate(pivot.columns):
                    fig_evs.add_trace(go.Bar(
                        name=ch, x=pivot.index, y=pivot[ch],
                        marker_color=COLORS[i % len(COLORS)],
                    ))
                layout_evs = chart_layout("Top Events by Channel", "Event", "Count")
                layout_evs["barmode"] = "group"
                fig_evs.update_layout(**layout_evs)
                st.plotly_chart(fig_evs, use_container_width=True)

    st.markdown("**All Events**")
    display_ev = events_df.rename(columns={
        "event": "Event Name", "count": "Event Count", "per_user": "Events per User"
    })
    display_ev["Events per User"] = display_ev["Events per User"].apply(lambda x: f"{x:.2f}")
    st.dataframe(display_ev, use_container_width=True, hide_index=True, height=350)
else:
    st.info("No event data available for this period.")
st.markdown("<br>", unsafe_allow_html=True)


# ── Top Pages with pagination + search ───────────────────────────────────────
st.markdown("#### Top Pages")
pages_df = pd.DataFrame(data["pages"])
if not pages_df.empty:
    search_term = st.text_input("Search pages", key="ga4_pages_search", placeholder="Filter by URL…")
    if "ga4_pages_last_search" not in st.session_state:
        st.session_state["ga4_pages_last_search"] = ""
    if search_term != st.session_state["ga4_pages_last_search"]:
        st.session_state["ga4_pages_page"] = 0
        st.session_state["ga4_pages_last_search"] = search_term

    filtered_pages = pages_df
    if search_term:
        mask = pages_df["page"].str.contains(search_term, case=False, na=False)
        filtered_pages = pages_df[mask]

    PAGE_SIZE = 10
    st.session_state.setdefault("ga4_pages_page", 0)
    total_rows   = len(filtered_pages)
    total_pages  = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)
    current_page = max(0, min(st.session_state["ga4_pages_page"], total_pages - 1))
    st.session_state["ga4_pages_page"] = current_page

    page_slice = filtered_pages.iloc[current_page * PAGE_SIZE: (current_page + 1) * PAGE_SIZE].copy()
    page_slice["avg_duration"] = page_slice["avg_duration"].apply(lambda x: f"{x:.1f}s")
    display_pages = page_slice.rename(columns={
        "page": "Page Path", "views": "Page Views",
        "sessions": "Sessions", "avg_duration": "Avg Duration"
    })
    st.dataframe(display_pages, use_container_width=True, hide_index=True)

    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("← Previous", disabled=(current_page == 0), key="ga4_pages_prev"):
            st.session_state["ga4_pages_page"] -= 1
            st.rerun()
    with col_info:
        st.caption(f"Page {current_page + 1} of {total_pages} · {total_rows:,} rows total")
    with col_next:
        if st.button("Next →", disabled=(current_page >= total_pages - 1), key="ga4_pages_next"):
            st.session_state["ga4_pages_page"] += 1
            st.rerun()

st.markdown("---")
st.caption(f"Data source: Google Analytics 4 · Property {property_id} · Refreshed hourly")
