import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.sidebar import render_sidebar
from utils.theme import get_theme, apply_theme_css, kpi_card, chart_layout, pct_delta, fmt_duration, CHANNEL_COLORS

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Calls — Goodman Financial", page_icon="📞",
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


def _rgba(hex_color: str, alpha: float = 0.40) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_callrail(start: str, end: str, api_key: str, account_id: str):
    import requests
    headers = {"Authorization": f'Token token="{api_key}"'}
    base    = f"https://api.callrail.com/v3/a/{account_id}"

    calls, page = [], 1
    while True:
        resp = requests.get(f"{base}/calls.json", headers=headers, timeout=30, params={
            "start_date": start, "end_date": end,
            "per_page": 250, "page": page,
            "fields": ("source_name,first_call,utm_source,utm_medium,utm_campaign,"
                       "keywords,device_type,lead_status,landing_page_url"),
        })
        resp.raise_for_status()
        data = resp.json()
        calls.extend(data.get("calls", []))
        if page >= int(data.get("total_pages", 1) or 1):
            break
        page += 1

    rows = []
    for c in calls:
        if c.get("direction") not in (None, "inbound"):
            continue  # count inbound calls only; outbound aren't leads
        rows.append({
            "time":         c.get("start_time", ""),
            "name":         c.get("customer_name", "") or "",
            "phone":        c.get("customer_phone_number", "") or "",
            "source":       c.get("source_name") or c.get("source") or "Unknown",
            "utm_source":   c.get("utm_source", "") or "",
            "utm_medium":   c.get("utm_medium", "") or "",
            "utm_campaign": c.get("utm_campaign", "") or "",
            "keywords":     c.get("keywords", "") or "",
            "device":       c.get("device_type", "") or "",
            "answered":     bool(c.get("answered")),
            "voicemail":    bool(c.get("voicemail")),
            "duration":     int(c.get("duration") or 0),
            "first_call":   bool(c.get("first_call")),
            "lead_status":  c.get("lead_status", "") or "",
        })

    answered = [r for r in rows if r["answered"]]
    return {
        "total":        len(rows),
        "first_time":   sum(1 for r in rows if r["first_call"]),
        "answered":     len(answered),
        "missed":       len(rows) - len(answered),
        "avg_duration": (sum(r["duration"] for r in answered) / len(answered)) if answered else 0.0,
        "calls":        rows,
    }


def render_setup_card():
    st.markdown(f"""
<div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-left:5px solid #D4A017;
            border-radius:10px;padding:2rem 2.5rem;max-width:720px;margin:2rem auto;
            box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <span style="font-size:1.8rem;">🔑</span>
        <h2 style="color:{theme['text_primary']};margin:0;font-size:1.3rem;font-weight:700;">CallRail Credentials Pending</h2>
    </div>
    <p style="color:{theme['text_primary']};margin:0 0 1rem;line-height:1.6;">
        This page is fully built and will display call tracking data as soon as credentials are added to
        <code style="background:{theme['bg']};padding:1px 5px;border-radius:3px;color:{theme['accent']};border:1px solid {theme['card_border']};">secrets.toml</code>.
    </p>
    <hr style="border-color:{theme['card_border']};margin:1.25rem 0;">
    <h3 style="color:{theme['accent']};font-size:1rem;margin:0 0 0.75rem;">Steps to connect CallRail</h3>
    <ol style="color:{theme['text_primary']};line-height:1.9;margin:0;padding-left:1.3rem;">
        <li><strong style="color:{theme['accent']};">API key</strong> — In CallRail: <em>Settings (gear) → Integrations → API Keys → Create New API V3 Key</em>.</li>
        <li><strong style="color:{theme['accent']};">Account ID</strong> — The number in your CallRail URL after signing in
            (<code style="color:{theme['accent']};">app.callrail.com/a/<strong>XXXXXXXXX</strong>/…</code>).</li>
    </ol>
    <hr style="border-color:{theme['card_border']};margin:1.25rem 0;">
    <pre style="background:{theme['bg']};border:1px solid {theme['card_border']};border-radius:6px;padding:1rem;
                font-size:0.85rem;color:{theme['accent']};overflow-x:auto;margin:0;">
CALLRAIL_API_KEY    = "your-v3-api-key"
CALLRAIL_ACCOUNT_ID = "123456789"</pre>
</div>
""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("CallRail · Credentials not yet configured")


# ── Page ─────────────────────────────────────────────────────────────────────
st.markdown("## Phone Calls (CallRail)")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

if not st.secrets.get("CALLRAIL_API_KEY", "") or not st.secrets.get("CALLRAIL_ACCOUNT_ID", ""):
    render_setup_card()
    st.stop()

api_key    = str(st.secrets["CALLRAIL_API_KEY"]).strip()
account_id = str(st.secrets["CALLRAIL_ACCOUNT_ID"]).strip()

with st.spinner("Fetching CallRail data…"):
    try:
        data = fetch_callrail(start_str, end_str, api_key, account_id)
    except Exception as e:
        st.error(f"Could not load CallRail data: {e}")
        st.markdown("**Checklist:**\n"
                    "- `CALLRAIL_API_KEY` must be an **API V3** key (Settings → Integrations → API Keys)\n"
                    "- `CALLRAIL_ACCOUNT_ID` is the number in your CallRail URL: `app.callrail.com/a/XXXXXXXXX/`\n"
                    "- The key must belong to a user with access to this account")
        st.stop()

prior_data = None
if compare_enabled and prior_start_str and prior_end_str:
    with st.spinner("Fetching comparison period…"):
        try:
            prior_data = fetch_callrail(prior_start_str, prior_end_str, api_key, account_id)
        except Exception:
            prior_data = None

if data["total"] == 0:
    st.info("No calls found for this date range.", icon="ℹ️")
    st.markdown("---")
    st.caption(f"CallRail API · Account {account_id} · No data for selected range")
    st.stop()

# ── KPI Cards ────────────────────────────────────────────────────────────────
p = prior_data
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(kpi_card("Total Calls",        f"{data['total']:,}",      pct_delta(data['total'],      p['total']      if p else None)), unsafe_allow_html=True)
c2.markdown(kpi_card("First-Time Callers", f"{data['first_time']:,}", pct_delta(data['first_time'], p['first_time'] if p else None)), unsafe_allow_html=True)
c3.markdown(kpi_card("Answered",           f"{data['answered']:,}",   pct_delta(data['answered'],   p['answered']   if p else None)), unsafe_allow_html=True)
c4.markdown(kpi_card("Missed",             f"{data['missed']:,}",     pct_delta(data['missed'],     p['missed']     if p else None), lower_is_better=True), unsafe_allow_html=True)
c5.markdown(kpi_card("Avg Duration",       fmt_duration(data['avg_duration']), pct_delta(data['avg_duration'], p['avg_duration'] if p else None)), unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

calls_df = pd.DataFrame(data["calls"])
calls_df["time"] = pd.to_datetime(calls_df["time"], errors="coerce", utc=True)

# ── Daily trend (answered vs missed) ─────────────────────────────────────────
daily = (calls_df.assign(date=calls_df["time"].dt.date)
                 .groupby(["date", "answered"]).size().unstack(fill_value=0)
                 .reindex(pd.date_range(start_date, end_date, freq="D").date, fill_value=0))
answered_daily = daily[True]  if True  in daily.columns else pd.Series(0, index=daily.index)
missed_daily   = daily[False] if False in daily.columns else pd.Series(0, index=daily.index)

fig = go.Figure()
fig.add_trace(go.Bar(x=list(daily.index), y=answered_daily.values, name="Answered",
                     marker_color=COLORS[0]))
fig.add_trace(go.Bar(x=list(daily.index), y=missed_daily.values, name="Missed",
                     marker_color=_rgba(theme["negative"], 0.75)))
layout = chart_layout("Calls per Day", "Date", "Calls")
layout["barmode"] = "stack"
layout["yaxis"]["dtick"] = 1
fig.update_layout(**layout, height=300)
st.plotly_chart(fig, use_container_width=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Calls by source ───────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    src_counts = calls_df["source"].value_counts()
    keys = src_counts.index.tolist()[::-1]
    fig2 = go.Figure(go.Bar(
        x=[src_counts[k] for k in keys], y=keys, orientation="h",
        marker_color=[CHANNEL_COLORS.get(k, COLORS[i % len(COLORS)]) for i, k in enumerate(keys)],
        text=[str(src_counts[k]) for k in keys],
        textposition="outside", textfont=dict(color=theme["chart_font"]),
    ))
    fig2.update_layout(**chart_layout("Calls by Source", compact=True),
                       height=max(280, len(keys) * 44 + 60))
    st.plotly_chart(fig2, use_container_width=True)

with col_r:
    ft_src = calls_df[calls_df["first_call"]]["source"].value_counts()
    if not ft_src.empty:
        keys_ft = ft_src.index.tolist()[::-1]
        fig3 = go.Figure(go.Bar(
            x=[ft_src[k] for k in keys_ft], y=keys_ft, orientation="h",
            marker_color=COLORS[1],
            text=[str(ft_src[k]) for k in keys_ft],
            textposition="outside", textfont=dict(color=theme["chart_font"]),
        ))
        fig3.update_layout(**chart_layout("First-Time Callers by Source", compact=True),
                           height=max(280, len(keys_ft) * 44 + 60))
        st.plotly_chart(fig3, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Campaign breakdown ────────────────────────────────────────────────────────
camp_df = calls_df[calls_df["utm_campaign"] != ""]
if not camp_df.empty:
    st.markdown("#### Calls by Campaign")
    camp_counts = (camp_df.groupby(["utm_source", "utm_medium", "utm_campaign"])
                          .size().reset_index(name="Calls")
                          .sort_values("Calls", ascending=False))
    camp_counts.columns = ["Source", "Medium", "Campaign", "Calls"]
    st.dataframe(camp_counts, use_container_width=True, hide_index=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ── Recent calls table ────────────────────────────────────────────────────────
st.markdown("#### Recent Calls")
disp = calls_df.sort_values("time", ascending=False).head(50).copy()
disp["time"]     = disp["time"].dt.strftime("%b %d, %Y %H:%M")
disp["duration"] = disp["duration"].apply(lambda s: fmt_duration(s) if s else "—")
disp["answered"] = disp["answered"].map({True: "✓", False: "✗"})
disp["first_call"] = disp["first_call"].map({True: "✓", False: ""})
disp = disp[["time", "name", "phone", "source", "utm_campaign", "keywords",
             "answered", "first_call", "duration"]]
disp.columns = ["Time", "Caller", "Phone", "Source", "Campaign", "Keywords",
                "Answered", "First Call", "Duration"]
st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

st.markdown("---")
st.caption(f"Data source: CallRail API · Account {account_id} · Refreshed every 30 min")
