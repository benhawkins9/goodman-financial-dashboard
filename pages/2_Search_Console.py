import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.sidebar import render_sidebar
from utils.theme import get_theme, apply_theme_css, kpi_card, chart_layout, pct_delta

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Search Console — Goodman Financial", page_icon="🔍",
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


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_gsc(start: str, end: str, site_url: str,
              project_id: str, private_key_id: str, private_key: str,
              client_email: str, client_id: str, client_x509: str):
    from googleapiclient.discovery import build
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
        creds_dict, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    service = build("searchconsole", "v1", credentials=credentials)

    def query(dimensions, row_limit=100, date_start=start, date_end=end):
        return service.searchanalytics().query(
            siteUrl=site_url,
            body={"startDate": date_start, "endDate": date_end,
                  "dimensions": dimensions, "rowLimit": row_limit},
        ).execute()

    totals_row = query([]).get("rows", [{}])[0]

    daily_rows = [{"date": r["keys"][0], "clicks": int(r["clicks"]),
                   "impressions": int(r["impressions"]), "ctr": r["ctr"] * 100,
                   "position": r["position"]}
                  for r in query(["date"], 90).get("rows", [])]

    queries_rows = [{"query": r["keys"][0], "clicks": int(r["clicks"]),
                     "impressions": int(r["impressions"]),
                     "ctr": round(r["ctr"] * 100, 2),
                     "position": round(r["position"], 1)}
                    for r in query(["query"], 200).get("rows", [])]

    pages_rows = [{"page": r["keys"][0], "clicks": int(r["clicks"]),
                   "impressions": int(r["impressions"]),
                   "ctr": round(r["ctr"] * 100, 2),
                   "position": round(r["position"], 1)}
                  for r in query(["page"], 200).get("rows", [])]

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

try:
    site_url         = st.secrets["GSC_SITE_URL"]
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

with st.spinner("Fetching Search Console data…"):
    try:
        data = fetch_gsc(start_str, end_str, site_url, *_creds_args)
    except Exception as e:
        st.error(f"Could not load Search Console data: {e}")
        st.stop()

prior_data = None
if compare_enabled and prior_start_str and prior_end_str:
    with st.spinner("Fetching comparison period…"):
        try:
            prior_data = fetch_gsc(prior_start_str, prior_end_str, site_url, *_creds_args)
        except Exception:
            prior_data = None


# ── KPI Cards ────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
kpis = [
    ("Total Clicks", f"{data['clicks']:,}",     pct_delta(data['clicks'],      prior_data['clicks']      if prior_data else None), False),
    ("Impressions",  f"{data['impressions']:,}", pct_delta(data['impressions'], prior_data['impressions'] if prior_data else None), False),
    ("Avg CTR",      f"{data['ctr']:.2f}%",      pct_delta(data['ctr'],         prior_data['ctr']         if prior_data else None), False),
    ("Avg Position", f"{data['position']:.1f}",  pct_delta(data['position'],    prior_data['position']    if prior_data else None), True),
]
for col, (title, val, delta, lib) in zip([c1, c2, c3, c4], kpis):
    col.markdown(kpi_card(title, val, delta, lower_is_better=lib), unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)


# ── Brand keyword & branded/non-branded split ─────────────────────────────────
st.markdown("#### Branded vs Non-Branded")
brand_kw = st.text_input(
    "Brand keyword (used to split branded vs. non-branded queries)",
    key="brand_keyword",
    placeholder="e.g. goodman",
)
if brand_kw:
    queries_df_all = pd.DataFrame(data["queries"])
    if not queries_df_all.empty:
        branded_mask   = queries_df_all["query"].str.contains(brand_kw, case=False, na=False)
        branded_df     = queries_df_all[branded_mask]
        non_branded_df = queries_df_all[~branded_mask]

        br_clicks  = int(branded_df["clicks"].sum())
        nbr_clicks = int(non_branded_df["clicks"].sum())
        br_impr    = int(branded_df["impressions"].sum())
        nbr_impr   = int(non_branded_df["impressions"].sum())

        bc1, bc2, bc3, bc4 = st.columns(4)
        bc1.markdown(kpi_card("Branded Clicks",     f"{br_clicks:,}"),  unsafe_allow_html=True)
        bc2.markdown(kpi_card("Non-Branded Clicks", f"{nbr_clicks:,}"), unsafe_allow_html=True)
        bc3.markdown(kpi_card("Branded Impr.",      f"{br_impr:,}"),    unsafe_allow_html=True)
        bc4.markdown(kpi_card("Non-Branded Impr.",  f"{nbr_impr:,}"),   unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


# ── Daily trend ──────────────────────────────────────────────────────────────
daily_df = pd.DataFrame(data["daily"])
if not daily_df.empty:
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    tab1, tab2 = st.tabs(["Clicks & Impressions", "CTR & Position"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=daily_df["date"], y=daily_df["impressions"],
                             name="Impressions", marker_color=theme["bar_fill"], yaxis="y2"))
        fig.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["clicks"],
                                 name="Clicks", line=dict(color=COLORS[0], width=2.5)))
        layout_args = chart_layout("Clicks vs Impressions", "Date")
        layout_args["barmode"] = "overlay"
        layout_args["yaxis"]  = dict(title="Clicks", gridcolor=theme["chart_grid"],
                                     color=theme["chart_axis"], tickfont=dict(color=theme["chart_axis"]),
                                     title_font=dict(color=theme["chart_axis"]))
        layout_args["yaxis2"] = dict(title="Impressions", overlaying="y", side="right",
                                     gridcolor="rgba(0,0,0,0)", color=theme["chart_axis"],
                                     tickfont=dict(color=theme["chart_axis"]),
                                     title_font=dict(color=theme["chart_axis"]))
        fig.update_layout(**layout_args)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["ctr"],
                                  name="CTR (%)", line=dict(color=COLORS[0], width=2.5)))
        fig2.add_trace(go.Scatter(x=daily_df["date"], y=daily_df["position"],
                                  name="Avg Position", line=dict(color=COLORS[1], width=2, dash="dot"),
                                  yaxis="y2"))
        layout_args2 = chart_layout("CTR & Avg Position", "Date")
        layout_args2["yaxis"]  = dict(title="CTR (%)", gridcolor=theme["chart_grid"],
                                      color=theme["chart_axis"], tickfont=dict(color=theme["chart_axis"]),
                                      title_font=dict(color=theme["chart_axis"]))
        layout_args2["yaxis2"] = dict(title="Avg Position (lower = better)", overlaying="y", side="right",
                                      autorange="reversed", gridcolor="rgba(0,0,0,0)",
                                      color=theme["chart_axis"], tickfont=dict(color=theme["chart_axis"]),
                                      title_font=dict(color=theme["chart_axis"]))
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
            textposition="outside", textfont=dict(color=theme["chart_font"]),
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
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        layout4 = chart_layout("Top Pages by Clicks")
        layout4["yaxis"]["autorange"] = "reversed"
        fig4.update_layout(**layout4, height=400)
        st.plotly_chart(fig4, use_container_width=True)


# ── Queries table with pagination + search ────────────────────────────────────
st.markdown("#### Top Queries — Detail")
if not queries_df.empty:
    q_search = st.text_input("Search queries", key="gsc_queries_search", placeholder="Filter by keyword…")
    if "gsc_queries_last_search" not in st.session_state:
        st.session_state["gsc_queries_last_search"] = ""
    if q_search != st.session_state["gsc_queries_last_search"]:
        st.session_state["gsc_queries_page"] = 0
        st.session_state["gsc_queries_last_search"] = q_search

    filtered_q = queries_df
    if q_search:
        filtered_q = queries_df[queries_df["query"].str.contains(q_search, case=False, na=False)]

    PAGE_SIZE = 10
    st.session_state.setdefault("gsc_queries_page", 0)
    total_q     = len(filtered_q)
    total_q_pgs = max(1, (total_q + PAGE_SIZE - 1) // PAGE_SIZE)
    cur_q_pg    = max(0, min(st.session_state["gsc_queries_page"], total_q_pgs - 1))
    st.session_state["gsc_queries_page"] = cur_q_pg

    q_slice = filtered_q.iloc[cur_q_pg * PAGE_SIZE: (cur_q_pg + 1) * PAGE_SIZE]
    st.dataframe(
        q_slice.rename(columns={"query": "Query", "clicks": "Clicks",
                                 "impressions": "Impressions", "ctr": "CTR (%)", "position": "Avg Position"}),
        use_container_width=True, hide_index=True,
    )
    col_p, col_i, col_n = st.columns([1, 3, 1])
    with col_p:
        if st.button("← Previous", disabled=(cur_q_pg == 0), key="gsc_q_prev"):
            st.session_state["gsc_queries_page"] -= 1
            st.rerun()
    with col_i:
        st.caption(f"Page {cur_q_pg + 1} of {total_q_pgs} · {total_q:,} queries")
    with col_n:
        if st.button("Next →", disabled=(cur_q_pg >= total_q_pgs - 1), key="gsc_q_next"):
            st.session_state["gsc_queries_page"] += 1
            st.rerun()


# ── Pages table with pagination + search ──────────────────────────────────────
st.markdown("#### Top Pages — Detail")
if not pages_df.empty:
    p_search = st.text_input("Search pages", key="gsc_pages_search", placeholder="Filter by URL…")
    if "gsc_pages_last_search" not in st.session_state:
        st.session_state["gsc_pages_last_search"] = ""
    if p_search != st.session_state["gsc_pages_last_search"]:
        st.session_state["gsc_pages_page"] = 0
        st.session_state["gsc_pages_last_search"] = p_search

    filtered_p = pages_df
    if p_search:
        filtered_p = pages_df[pages_df["page"].str.contains(p_search, case=False, na=False)]

    PAGE_SIZE = 10
    st.session_state.setdefault("gsc_pages_page", 0)
    total_p     = len(filtered_p)
    total_p_pgs = max(1, (total_p + PAGE_SIZE - 1) // PAGE_SIZE)
    cur_p_pg    = max(0, min(st.session_state["gsc_pages_page"], total_p_pgs - 1))
    st.session_state["gsc_pages_page"] = cur_p_pg

    p_slice = filtered_p.iloc[cur_p_pg * PAGE_SIZE: (cur_p_pg + 1) * PAGE_SIZE]
    st.dataframe(
        p_slice.rename(columns={"page": "Page URL", "clicks": "Clicks",
                                 "impressions": "Impressions", "ctr": "CTR (%)", "position": "Avg Position"}),
        use_container_width=True, hide_index=True,
    )
    col_p2, col_i2, col_n2 = st.columns([1, 3, 1])
    with col_p2:
        if st.button("← Previous", disabled=(cur_p_pg == 0), key="gsc_p_prev"):
            st.session_state["gsc_pages_page"] -= 1
            st.rerun()
    with col_i2:
        st.caption(f"Page {cur_p_pg + 1} of {total_p_pgs} · {total_p:,} pages")
    with col_n2:
        if st.button("Next →", disabled=(cur_p_pg >= total_p_pgs - 1), key="gsc_p_next"):
            st.session_state["gsc_pages_page"] += 1
            st.rerun()

st.markdown("---")
st.caption(f"Data source: Google Search Console · {site_url} · Refreshed hourly")
