import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.sidebar import render_sidebar
from utils.theme import (
    get_theme, apply_theme_css, kpi_card, chart_layout,
    pct_delta, fmt_number, CHANNEL_COLORS,
)

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import requests
import hmac
import hashlib
import base64
import time
import json

st.set_page_config(
    page_title="Leads — Goodman Financial",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

dates           = render_sidebar()
start_date      = dates["start_date"]
end_date        = dates["end_date"]
compare_enabled = dates["compare_enabled"]
prior_start     = dates["prior_start"]
prior_end       = dates["prior_end"]

theme = get_theme()
apply_theme_css(theme)

def _rgba(hex_color: str, alpha: float = 0.40) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Config ────────────────────────────────────────────────────────────────────
FORM_FIELD_MAP = {
    "1": {
        "12": "utm_source",
        "13": "utm_medium",
        "14": "utm_campaign",
        "15": "utm_content",
        "16": "referring_url",
    },
    "14": {
        "7":  "utm_source",
        "8":  "utm_medium",
        "9":  "utm_campaign",
        "10": "utm_content",
        "11": "referring_url",
    },
}

FORM_NAMES = {
    "1":  "Contact Form",
    "14": "Discovery Call",
}


# ── Authentication ────────────────────────────────────────────────────────────
def get_gf_auth():
    api_key     = st.secrets["GF_API_KEY"]
    private_key = st.secrets["GF_PRIVATE_KEY"]
    expires     = int(time.time()) + 3600
    string_to_sign = f"{api_key}:{expires}"
    sig = base64.b64encode(
        hmac.new(
            private_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")
    return api_key, sig, expires


# ── API debug ─────────────────────────────────────────────────────────────────
def test_gf_connection():
    api_key, sig, expires = get_gf_auth()
    base = st.secrets["GF_SITE_URL"].rstrip("/")

    # Test basic API connectivity
    test_url = f"{base}/gravityformsapi/?api_key={api_key}&signature={sig}&expires={expires}"

    try:
        resp = requests.get(test_url, timeout=30)
        st.write("Status code:", resp.status_code)
        st.write("Response headers:", dict(resp.headers))
        st.write("Raw response (first 500 chars):", resp.text[:500])
    except Exception as e:
        st.write("Connection error:", str(e))


# ── Fetch entries ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_gf_entries(start_date, end_date):
    api_key, sig, expires = get_gf_auth()
    base     = st.secrets["GF_SITE_URL"].rstrip("/")
    form_ids = st.secrets["GF_FORM_IDS"].split(",")

    all_entries = []
    for form_id in form_ids:
        page = 1
        while True:
            search = json.dumps({
                "start_date": str(start_date),
                "end_date":   str(end_date),
            })
            url = (
                f"{base}/gravityformsapi/entries/"
                f"?api_key={api_key}&signature={sig}&expires={expires}"
                f"&form_ids[]={form_id.strip()}"
                f"&paging[page_size]=100&paging[current_page]={page}"
                f"&search={search}"
            )
            resp = requests.get(url, timeout=30)
            data = resp.json()

            if not data.get("response") or not data["response"].get("entries"):
                break

            entries = data["response"]["entries"]
            all_entries.extend(entries)

            total = data["response"].get("total_count", 0)
            if len(all_entries) >= int(total):
                break
            page += 1

    return all_entries


# ── Build DataFrame ───────────────────────────────────────────────────────────
def build_df(entries: list) -> pd.DataFrame:
    rows = []
    for entry in entries:
        form_id  = str(entry.get("form_id", ""))
        field_map = FORM_FIELD_MAP.get(form_id, {})

        row = {
            "date":          entry.get("date_created", ""),
            "form_id":       form_id,
            "form_name":     FORM_NAMES.get(form_id, f"Form {form_id}"),
            "utm_source":    "",
            "utm_medium":    "",
            "utm_campaign":  "",
            "utm_content":   "",
            "referring_url": "",
        }

        for field_id, col_name in field_map.items():
            row[col_name] = entry.get(field_id, "") or ""

        # Defaults for attribution fields
        if not row["utm_source"].strip():
            row["utm_source"] = "direct"
        if not row["utm_medium"].strip():
            row["utm_medium"] = "none"

        rows.append(row)

    df = pd.DataFrame(rows, columns=[
        "date", "form_name", "utm_source", "utm_medium",
        "utm_campaign", "utm_content", "referring_url",
    ])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# ── Secrets check ─────────────────────────────────────────────────────────────
_missing = [k for k in ("GF_SITE_URL", "GF_API_KEY", "GF_PRIVATE_KEY", "GF_FORM_IDS")
            if not st.secrets.get(k, "")]
if _missing:
    st.error(f"Missing secrets: {', '.join(_missing)}. Add them to `.streamlit/secrets.toml`.")
    st.info("""
```toml
GF_SITE_URL    = "https://www.yoursite.com"
GF_API_KEY     = "your_api_key"
GF_PRIVATE_KEY = "your_private_key"
GF_FORM_IDS    = "1,14"
```
    """)
    st.stop()


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("# Lead Attribution")
st.markdown(
    f'<p style="color:{theme["text_secondary"]};margin-top:-0.5rem;">'
    f'Gravity Forms entries with UTM tracking — '
    f'{start_date.strftime("%b %d, %Y")} to {end_date.strftime("%b %d, %Y")}'
    + (f' &nbsp;·&nbsp; vs. {prior_start.strftime("%b %d")} – {prior_end.strftime("%b %d, %Y")}'
       if compare_enabled and prior_start else "")
    + "</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

if st.button("Test API Connection"):
    test_gf_connection()


# ── Fetch data ────────────────────────────────────────────────────────────────
raw_entries   = []
p_raw_entries = []

with st.spinner("Loading leads from Gravity Forms…"):
    try:
        raw_entries = fetch_gf_entries(start_date, end_date)
    except Exception as e:
        st.error("Could not connect to Gravity Forms API. "
                 "Check GF_SITE_URL, GF_API_KEY, and GF_PRIVATE_KEY in secrets.")
        with st.expander("Error details"):
            st.code(str(e))
        st.stop()

if compare_enabled and prior_start:
    with st.spinner("Loading prior period leads…"):
        try:
            p_raw_entries = fetch_gf_entries(prior_start, prior_end)
        except Exception:
            p_raw_entries = []

df      = build_df(raw_entries)
p_df    = build_df(p_raw_entries)
total   = len(df)
p_total = len(p_df)
d_total = pct_delta(total, p_total) if compare_enabled and p_total else None


# ── KPI cards ─────────────────────────────────────────────────────────────────
top_source   = df["utm_source"].value_counts().idxmax()   if total else "—"
top_medium   = df["utm_medium"].value_counts().idxmax()   if total else "—"
camp_df      = df[~df["utm_campaign"].isin(["", "none", "direct", "(not set)"])]
top_campaign = camp_df["utm_campaign"].value_counts().idxmax() if not camp_df.empty else "None"

k1, k2, k3, k4 = st.columns(4)
k1.markdown(kpi_card("Total Leads",   fmt_number(total),  delta=d_total), unsafe_allow_html=True)
k2.markdown(kpi_card("Top Source",    top_source),                        unsafe_allow_html=True)
k3.markdown(kpi_card("Top Medium",    top_medium),                        unsafe_allow_html=True)
k4.markdown(kpi_card("Top Campaign",  top_campaign),                      unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if df.empty:
    st.info("No leads found for this date range.")
    st.stop()


# ── Leads Over Time ───────────────────────────────────────────────────────────
daily = (df.set_index("date")
           .resample("D").size()
           .reindex(pd.date_range(start_date, end_date, freq="D"), fill_value=0)
           .rename("Leads"))

fig_time = go.Figure()

if compare_enabled and not p_df.empty:
    p_daily = (p_df.set_index("date")
                   .resample("D").size()
                   .reindex(pd.date_range(prior_start, prior_end, freq="D"), fill_value=0)
                   .rename("Leads"))
    # Overlay by day-of-period offset so periods align visually
    fig_time.add_trace(go.Scatter(
        x=list(range(len(p_daily))), y=p_daily.values,
        name=f"Prior ({prior_start.strftime('%b %d')} – {prior_end.strftime('%b %d')})",
        line=dict(color=theme["accent"], width=2, dash="dot"),
        mode="lines",
        hovertemplate="Day %{x}: %{y} lead(s)<extra>Prior Period</extra>",
    ))
    fig_time.add_trace(go.Scatter(
        x=list(range(len(daily))), y=daily.values,
        name=f"Current ({start_date.strftime('%b %d')} – {end_date.strftime('%b %d')})",
        line=dict(color=theme["accent"], width=2.5),
        fill="tozeroy", fillcolor=_rgba(theme["accent"], 0.12),
        mode="lines",
        hovertemplate="Day %{x}: %{y} lead(s)<extra>Current Period</extra>",
    ))
    layout_time = chart_layout("Leads by Day", "Day of Period", "Leads")
    fig_time.update_layout(**layout_time, height=300)
    fig_time.update_xaxes(showticklabels=False)
else:
    fig_time.add_trace(go.Scatter(
        x=daily.index, y=daily.values,
        name="Leads",
        line=dict(color=theme["accent"], width=2.5),
        fill="tozeroy", fillcolor=_rgba(theme["accent"], 0.12),
        mode="lines",
        hovertemplate="%{x|%b %d}: %{y} lead(s)<extra></extra>",
    ))
    layout_time = chart_layout("Leads by Day", "Date", "Leads")
    layout_time["yaxis"]["dtick"] = 1
    fig_time.update_layout(**layout_time, height=300)

st.plotly_chart(fig_time, use_container_width=True)
st.markdown("<br>", unsafe_allow_html=True)


# ── Bar chart helper ──────────────────────────────────────────────────────────
def _source_color(val: str, idx: int = 0) -> str:
    return CHANNEL_COLORS.get(val, theme["colors"][idx % len(theme["colors"])])

def _bar_delta_label(c, p):
    if not p: return str(c)
    pct = (c - p) / p * 100
    return f"{c}  {'↑' if pct >= 0 else '↓'}{abs(pct):.0f}%"

def _bar_delta_color(c, p):
    if not p: return theme["chart_font"]
    return theme["accent"] if c >= p else theme["negative"]

def _compare_hbar(cur_counts: pd.Series, pri_counts: pd.Series | None,
                  title: str, use_channel_colors: bool = False) -> go.Figure:
    """Build a horizontal grouped bar (or single bar) chart."""
    cur_map = cur_counts.to_dict()
    pri_map = pri_counts.to_dict() if pri_counts is not None else {}

    if compare_enabled and pri_map:
        all_keys = sorted(
            cur_map.keys() | pri_map.keys(),
            key=lambda k: cur_map.get(k, 0),
        )
        cur_vals = [cur_map.get(k, 0) for k in all_keys]
        pri_vals = [pri_map.get(k, 0) for k in all_keys]

        if use_channel_colors:
            colors = [_source_color(k, i) for i, k in enumerate(all_keys)]
        else:
            colors = [theme["colors"][i % len(theme["colors"])] for i, k in enumerate(all_keys)]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=cur_vals, y=list(all_keys), orientation="h",
            name="Current", marker_color=colors, width=0.6,
            text=[_bar_delta_label(cur_map.get(k, 0), pri_map.get(k, 0)) for k in all_keys],
            textposition="outside",
            textfont=dict(color=[_bar_delta_color(cur_map.get(k, 0), pri_map.get(k, 0))
                                  for k in all_keys]),
        ))
        fig.add_trace(go.Bar(
            x=pri_vals, y=list(all_keys), orientation="h",
            name="Prior",
            marker_color=[_rgba(c, 0.35) for c in colors],
            width=0.4,
            text=[str(v) for v in pri_vals],
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        layout = chart_layout(title, compact=True)
        layout["barmode"] = "group"
        fig.update_layout(**layout, height=max(300, len(all_keys) * 80))
    else:
        keys = sorted(cur_map.keys(), key=lambda k: cur_map[k])
        vals = [cur_map[k] for k in keys]
        if use_channel_colors:
            colors = [_source_color(k, i) for i, k in enumerate(keys)]
        else:
            colors = [theme["colors"][i % len(theme["colors"])] for i, k in enumerate(keys)]
        fig = go.Figure(go.Bar(
            x=vals, y=list(keys), orientation="h",
            marker_color=colors,
            text=[str(v) for v in vals],
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        fig.update_layout(
            **chart_layout(title, compact=True),
            height=max(280, len(keys) * 44 + 60),
        )
    return fig


# ── Leads by Source ───────────────────────────────────────────────────────────
src_counts   = df["utm_source"].value_counts()
p_src_counts = p_df["utm_source"].value_counts() if compare_enabled and not p_df.empty else None

fig_src = _compare_hbar(src_counts, p_src_counts, "Leads by Source", use_channel_colors=True)
st.plotly_chart(fig_src, use_container_width=True)
st.markdown("<br>", unsafe_allow_html=True)


# ── Leads by Medium ───────────────────────────────────────────────────────────
med_counts   = df["utm_medium"].value_counts()
p_med_counts = p_df["utm_medium"].value_counts() if compare_enabled and not p_df.empty else None

fig_med = _compare_hbar(med_counts, p_med_counts, "Leads by Medium")
st.plotly_chart(fig_med, use_container_width=True)
st.markdown("<br>", unsafe_allow_html=True)


# ── Leads by Campaign ─────────────────────────────────────────────────────────
_excl = {"", "none", "direct", "(not set)", "(none)"}
camp_series   = df[~df["utm_campaign"].str.lower().isin(_excl)]["utm_campaign"].value_counts()
p_camp_series = (p_df[~p_df["utm_campaign"].str.lower().isin(_excl)]["utm_campaign"].value_counts()
                 if compare_enabled and not p_df.empty else None)

if camp_series.empty:
    st.markdown(
        f'<p style="color:{theme["text_secondary"]};font-size:0.9rem;'
        f'padding:1rem 0;">No campaign data yet</p>',
        unsafe_allow_html=True,
    )
else:
    fig_camp = _compare_hbar(camp_series, p_camp_series, "Leads by Campaign")
    st.plotly_chart(fig_camp, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Source + Medium breakdown table ──────────────────────────────────────────
st.markdown("#### Source & Medium Breakdown")
src_med = (df.groupby(["utm_source", "utm_medium"])
             .size()
             .reset_index(name="Leads")
             .sort_values("Leads", ascending=False))
src_med["% of Total"] = (src_med["Leads"] / total * 100).map(lambda x: f"{x:.1f}%")
src_med = src_med.rename(columns={"utm_source": "Source", "utm_medium": "Medium"})
st.dataframe(src_med[["Source", "Medium", "Leads", "% of Total"]],
             use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Recent Entries Table (paginated) ─────────────────────────────────────────
st.markdown("#### Recent Entries")

display_df = df.copy()
display_df["date"] = display_df["date"].dt.strftime("%b %d, %Y %H:%M")
display_df["referring_url"] = display_df["referring_url"].apply(
    lambda u: (str(u)[:40] + "…") if len(str(u)) > 40 else str(u)
)
display_df = display_df.rename(columns={
    "date":          "Date",
    "form_name":     "Form",
    "utm_source":    "Source",
    "utm_medium":    "Medium",
    "utm_campaign":  "Campaign",
    "utm_content":   "Content",
    "referring_url": "Referring URL",
})
display_df = display_df.drop(columns=["form_id"], errors="ignore")
display_df = display_df.sort_values("Date", ascending=False).reset_index(drop=True)

page_size = 10
total_pages = max(1, (len(display_df) + page_size - 1) // page_size)

if "leads_page" not in st.session_state:
    st.session_state["leads_page"] = 1
st.session_state["leads_page"] = max(1, min(st.session_state["leads_page"], total_pages))

page_num = st.session_state["leads_page"]
page_start = (page_num - 1) * page_size
page_df    = display_df.iloc[page_start : page_start + page_size]

st.dataframe(page_df, use_container_width=True, hide_index=True)

nav_left, nav_mid, nav_right = st.columns([1, 2, 1])
with nav_left:
    if st.button("← Prev", disabled=(page_num <= 1), key="leads_prev"):
        st.session_state["leads_page"] -= 1
        st.rerun()
with nav_mid:
    st.markdown(
        f'<p style="text-align:center;color:{theme["text_secondary"]};">'
        f'Page {page_num} of {total_pages} &nbsp;·&nbsp; {total:,} entries</p>',
        unsafe_allow_html=True,
    )
with nav_right:
    if st.button("Next →", disabled=(page_num >= total_pages), key="leads_next"):
        st.session_state["leads_page"] += 1
        st.rerun()

st.markdown("---")
st.caption(
    f"Forms: {', '.join(FORM_NAMES.values())} · "
    f"{total:,} entries fetched · "
    f"Refreshed every 30 min"
)
