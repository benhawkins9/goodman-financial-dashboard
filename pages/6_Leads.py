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
from requests.auth import HTTPBasicAuth
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


# Browser-like headers so Cloudflare's Bot Fight Mode lets the request
# through. The default `python-requests/X.Y.Z` user-agent is 403'd at the
# edge.
GF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Authentication ────────────────────────────────────────────────────────────
# Gravity Forms REST API v2 uses HTTP Basic Auth with a Consumer Key /
# Consumer Secret pair generated under WP Admin → Forms → Settings →
# REST API → API Version 2 → Add Key. We re-use the existing
# GF_API_KEY / GF_PRIVATE_KEY secrets as those credentials.
def get_gf_basic_auth() -> HTTPBasicAuth:
    return HTTPBasicAuth(
        st.secrets["GF_API_KEY"],
        st.secrets["GF_PRIVATE_KEY"],
    )


# ── API debug ─────────────────────────────────────────────────────────────────
def test_gf_connection():
    base = st.secrets["GF_SITE_URL"].rstrip("/")
    # GF v2 root: /wp-json/gf/v2 — should return a small JSON descriptor
    test_url = f"{base}/wp-json/gf/v2/forms"

    try:
        resp = requests.get(
            test_url, timeout=30,
            headers=GF_HEADERS, auth=get_gf_basic_auth(),
        )
        st.write("Status code:", resp.status_code)
        st.write("Response headers:", dict(resp.headers))
        st.write("Raw response (first 500 chars):", resp.text[:500])
    except Exception as e:
        st.write("Connection error:", str(e))


# ── Form schema (auto-discover name / email / phone field IDs) ───────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_gf_form_schemas() -> dict:
    """Return {form_id: {"name_first": "1.3", "name_last": "1.6",
                          "email": "3", "phone": "4"}} for the configured forms.

    Falls back to label-based matching when fields aren't typed as
    name/email/phone.
    """
    base     = st.secrets["GF_SITE_URL"].rstrip("/")
    form_ids = [f.strip() for f in st.secrets["GF_FORM_IDS"].split(",")]
    auth     = get_gf_basic_auth()

    schemas: dict = {}
    for form_id in form_ids:
        try:
            resp = requests.get(
                f"{base}/wp-json/gf/v2/forms/{form_id}",
                timeout=20, headers=GF_HEADERS, auth=auth,
            )
            resp.raise_for_status()
            form = resp.json()
        except Exception:
            schemas[form_id] = {}
            continue

        slot: dict = {}
        for field in form.get("fields", []):
            ftype = (field.get("type") or "").lower()
            label = (field.get("label") or "").lower()
            fid   = str(field.get("id") or "")

            if ftype == "name" or "name" in label:
                # Name field: prefer first/last sub-inputs
                for inp in field.get("inputs") or []:
                    sub_label = (inp.get("label") or "").lower()
                    sub_id    = str(inp.get("id") or "")
                    if "first" in sub_label and "name_first" not in slot:
                        slot["name_first"] = sub_id
                    elif "last" in sub_label and "name_last" not in slot:
                        slot["name_last"] = sub_id
                if not field.get("inputs") and "name_full" not in slot:
                    slot["name_full"] = fid
            elif ftype == "email" or "email" in label:
                slot.setdefault("email", fid)
            elif ftype == "phone" or "phone" in label:
                slot.setdefault("phone", fid)

        schemas[form_id] = slot
    return schemas


# ── Fetch entries ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_gf_entries(start_date, end_date):
    base     = st.secrets["GF_SITE_URL"].rstrip("/")
    form_ids = st.secrets["GF_FORM_IDS"].split(",")
    auth     = get_gf_basic_auth()

    all_entries: list = []
    for form_id in form_ids:
        form_entries: list = []
        page = 1
        while True:
            search = json.dumps({
                "start_date": str(start_date),
                "end_date":   str(end_date),
            })
            params = {
                "form_ids[]":           form_id.strip(),
                "paging[page_size]":    100,
                "paging[current_page]": page,
                "search":               search,
            }
            url = f"{base}/wp-json/gf/v2/entries"
            resp = requests.get(url, params=params, timeout=30,
                                 headers=GF_HEADERS, auth=auth)
            resp.raise_for_status()
            data = resp.json()

            entries = data.get("entries") or []
            if not entries:
                break

            form_entries.extend(entries)
            total = int(data.get("total_count", 0) or 0)
            if total and len(form_entries) >= total:
                break
            page += 1
        all_entries.extend(form_entries)

    return all_entries


# ── Referrer → source/medium fallback ────────────────────────────────────────
# When a visitor arrives without UTM params (e.g. an organic LinkedIn click
# with no campaign tagging), the form's hidden utm_* fields are blank but
# the referring_url field still captures the source. We derive a
# source/medium pair from the referrer hostname so those visits don't
# silently default to "direct".
_REFERRER_RULES = [
    ("linkedin.com",   ("linkedin",   "referral")),
    ("lnkd.in",        ("linkedin",   "referral")),
    ("facebook.com",   ("facebook",   "referral")),
    ("fb.com",         ("facebook",   "referral")),
    ("instagram.com",  ("instagram",  "referral")),
    ("chatgpt.com",    ("chatgpt",    "referral")),
    ("openai.com",     ("chatgpt",    "referral")),
    ("perplexity.ai",  ("perplexity", "referral")),
    ("bing.com",       ("bing",       "organic")),
    ("duckduckgo.com", ("duckduckgo", "organic")),
    ("google.",        ("google",     "organic")),
    ("youtube.com",    ("youtube",    "referral")),
    ("twitter.com",    ("twitter",    "referral")),
    ("x.com",          ("twitter",    "referral")),
    ("reddit.com",     ("reddit",     "referral")),
]

def _derive_source_from_referrer(referring_url: str) -> tuple[str, str] | None:
    """Return (source, medium) inferred from a referring URL, or None."""
    if not referring_url:
        return None
    host = referring_url.lower()
    # Strip protocol and path quickly without importing urlparse
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0]
    for needle, pair in _REFERRER_RULES:
        if needle in host:
            return pair
    return None


# ── Build DataFrame ───────────────────────────────────────────────────────────
def build_df(entries: list, schemas: dict | None = None) -> pd.DataFrame:
    schemas = schemas or {}
    rows = []
    for entry in entries:
        form_id   = str(entry.get("form_id", ""))
        field_map = FORM_FIELD_MAP.get(form_id, {})
        slot      = schemas.get(form_id, {})

        # Pull contact fields based on the auto-discovered schema
        name_parts = []
        if "name_first" in slot:
            name_parts.append(str(entry.get(slot["name_first"], "") or "").strip())
        if "name_last" in slot:
            name_parts.append(str(entry.get(slot["name_last"], "") or "").strip())
        if not name_parts and "name_full" in slot:
            name_parts.append(str(entry.get(slot["name_full"], "") or "").strip())
        contact_name = " ".join(p for p in name_parts if p)

        row = {
            "date":          entry.get("date_created", ""),
            "form_id":       form_id,
            "form_name":     FORM_NAMES.get(form_id, f"Form {form_id}"),
            "name":          contact_name,
            "email":         str(entry.get(slot.get("email", ""), "") or "").strip(),
            "phone":         str(entry.get(slot.get("phone", ""), "") or "").strip(),
            "utm_source":    "",
            "utm_medium":    "",
            "utm_campaign":  "",
            "utm_content":   "",
            "referring_url": "",
        }

        for field_id, col_name in field_map.items():
            row[col_name] = entry.get(field_id, "") or ""

        # If UTMs are empty but we captured a referring URL, derive
        # source/medium from the referrer hostname (LinkedIn, Facebook,
        # ChatGPT, Google organic, etc.) before falling back to direct.
        if not row["utm_source"].strip():
            inferred = _derive_source_from_referrer(row.get("referring_url", ""))
            if inferred:
                row["utm_source"], row["utm_medium"] = inferred

        if not row["utm_source"].strip():
            row["utm_source"] = "direct"
        if not row["utm_medium"].strip():
            row["utm_medium"] = "none"

        rows.append(row)

    df = pd.DataFrame(rows, columns=[
        "date", "form_name", "name", "email", "phone",
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "referring_url",
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
form_schemas: dict = {}

with st.spinner("Loading leads from Gravity Forms…"):
    try:
        form_schemas = fetch_gf_form_schemas()
    except Exception:
        form_schemas = {}
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

df      = build_df(raw_entries,   form_schemas)
p_df    = build_df(p_raw_entries, form_schemas)
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
    "name":          "Name",
    "email":         "Email",
    "phone":         "Phone",
    "utm_source":    "Source",
    "utm_medium":    "Medium",
    "utm_campaign":  "Campaign",
    "utm_content":   "Content",
    "referring_url": "Referring URL",
})
display_df = display_df.drop(columns=["form_id"], errors="ignore")
# Reorder so contact info sits next to date / form for easy scanning
display_df = display_df[[
    "Date", "Form", "Name", "Email", "Phone",
    "Source", "Medium", "Campaign", "Content", "Referring URL",
]]
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
