import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.sidebar import render_sidebar

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="LinkedIn — Goodman Financial", page_icon="💼",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
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
.stButton>button:not([kind="primary"]){background-color:#FFFFFF!important;border-color:#E2E8E4!important;color:#1A1A2E!important;border-radius:6px;}
.stTabs [data-baseweb="tab-list"]{background-color:transparent;border-bottom:2px solid #E2E8E4;}
.stTabs [data-baseweb="tab"]{color:#6B7280!important;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{border-bottom:3px solid #0F6E56!important;color:#1A1A2E!important;font-weight:600;}
[data-testid="stDataFrame"]{border:1px solid #E2E8E4;border-radius:8px;}
[data-testid="stAlert"]{background-color:#F0F7F4!important;border-color:#E2E8E4!important;}
hr{border-color:#E2E8E4!important;}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

COLORS = ["#0F6E56", "#1A9E7A", "#5BB89A", "#8ECFC0", "#3D8B70", "#2A6B55"]

dates = render_sidebar()
start_date = dates["start_date"]
end_date   = dates["end_date"]

def kpi_card(title, value):
    return f"""<div style="background:#FFFFFF;border:1px solid #E2E8E4;border-left:4px solid #0F6E56;
                border-radius:8px;padding:1.1rem 1.25rem;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <p style="color:#6B7280;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px;">{title}</p>
        <h2 style="color:#1A1A2E;font-size:28px;font-weight:600;margin:0;">{value}</h2>
    </div>"""

def chart_layout(title="", xaxis_title="", yaxis_title=""):
    return dict(
        title=dict(text=title, font=dict(size=15, color="#1A1A2E"), x=0),
        plot_bgcolor="#FAFAFA", paper_bgcolor="#FFFFFF",
        font=dict(family="Inter, sans-serif", color="#1A1A2E"),
        xaxis=dict(title=xaxis_title, gridcolor="#F0F0F0", linecolor="#E2E8E4",
                   color="#6B7280", tickfont=dict(color="#6B7280"), title_font=dict(color="#6B7280")),
        yaxis=dict(title=yaxis_title, gridcolor="#F0F0F0", linecolor="#E2E8E4",
                   color="#6B7280", tickfont=dict(color="#6B7280"), title_font=dict(color="#6B7280")),
        margin=dict(t=50, b=40, l=50, r=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#1A1A2E")),
        hovermode="x unified",
    )

COLUMN_MAP = {
    "impressions": "Impressions", "impression": "Impressions", "total impressions": "Impressions",
    "clicks": "Clicks", "click": "Clicks", "link clicks": "Clicks",
    "ctr": "CTR (%)", "click-through rate": "CTR (%)", "click through rate": "CTR (%)",
    "spend": "Spend ($)", "amount spent": "Spend ($)", "cost": "Spend ($)",
    "engagements": "Engagements", "total engagements": "Engagements",
    "followers": "Followers", "new followers": "New Followers",
    "date": "Date", "week": "Week", "month": "Month", "period": "Period",
    "conversions": "Conversions", "leads": "Leads", "form submissions": "Leads",
}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_sheet(sheet_id: str, project_id: str, private_key_id: str, private_key: str,
                client_email: str, client_id: str, client_x509_cert_url: str) -> pd.DataFrame:
    import gspread
    from google.oauth2.service_account import Credentials
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
        "client_x509_cert_url": client_x509_cert_url,
        "universe_domain": "googleapis.com",
    }
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(sheet_id).get_worksheet(0)
    return pd.DataFrame(ws.get_all_records())


# ── Page ─────────────────────────────────────────────────────────────────────
st.markdown("## LinkedIn")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

try:
    sheet_id        = st.secrets["LINKEDIN_SHEET_ID"]
    _project_id     = st.secrets["GA4_PROJECT_ID"]
    _private_key_id = st.secrets["GA4_PRIVATE_KEY_ID"]
    _private_key    = st.secrets["GA4_PRIVATE_KEY"]
    _client_email   = st.secrets["GA4_CLIENT_EMAIL"]
    _client_id      = st.secrets["GA4_CLIENT_ID"]
    _client_x509    = st.secrets["GA4_CLIENT_X509_CERT_URL"]
except KeyError as e:
    st.error(f"Missing secret: {e}. Add LINKEDIN_SHEET_ID and all GA4_* secrets to secrets.toml.")
    st.stop()

with st.spinner("Loading LinkedIn data from Google Sheet…"):
    try:
        raw_df = fetch_sheet(sheet_id, _project_id, _private_key_id, _private_key,
                             _client_email, _client_id, _client_x509)
    except Exception as e:
        st.error(f"Could not load Google Sheet: {e}")
        st.info(f"Make sure the sheet is shared with: `{_client_email}`")
        st.stop()

if raw_df.empty:
    st.warning("The Google Sheet appears to be empty.")
    st.stop()

# Normalise columns
rename = {}
for col in raw_df.columns:
    canonical = COLUMN_MAP.get(col.strip().lower())
    if canonical and canonical not in raw_df.columns:
        rename[col] = canonical
df = raw_df.rename(columns=rename)

# Date filter
date_col = next((c for c in ["Date","Week","Month","Period"] if c in df.columns), None)
filtered_df = df.copy()
if date_col:
    try:
        filtered_df[date_col] = pd.to_datetime(filtered_df[date_col], infer_datetime_format=True, errors="coerce")
        mask = (filtered_df[date_col].dt.date >= start_date) & (filtered_df[date_col].dt.date <= end_date)
        if mask.any():
            filtered_df = filtered_df[mask]
    except Exception:
        pass

num_cols = [c for c in filtered_df.columns if pd.api.types.is_numeric_dtype(filtered_df[c])]
PRIORITY = ["Impressions","Clicks","Engagements","Spend ($)","CTR (%)","Conversions","Leads","Followers","New Followers"]
kpi_cols = [c for c in PRIORITY if c in filtered_df.columns] or num_cols[:6]

# ── KPI cards ─────────────────────────────────────────────────────────────────
if kpi_cols:
    rows_needed = (len(kpi_cols) + 3) // 4
    for row_i in range(rows_needed):
        batch = kpi_cols[row_i*4:(row_i+1)*4]
        cols = st.columns(len(batch))
        for i, col_name in enumerate(batch):
            total = pd.to_numeric(filtered_df[col_name], errors="coerce").sum()
            if "($)" in col_name or "spend" in col_name.lower():
                val = f"${total:,.2f}"
            elif "(%)" in col_name:
                val = f"{total:.2f}%"
            else:
                val = f"{int(total):,}" if total == int(total) else f"{total:,.2f}"
            cols[i].markdown(kpi_card(col_name, val), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Trend chart ───────────────────────────────────────────────────────────────
if date_col and num_cols:
    chart_candidates = [c for c in ["Impressions","Clicks","Engagements"] if c in filtered_df.columns] or num_cols[:3]
    if chart_candidates:
        st.markdown("#### Trend Over Time")
        selected = st.multiselect("Metrics to plot", chart_candidates, default=chart_candidates[:2])
        if selected:
            trend_df = filtered_df[[date_col] + selected].dropna(subset=[date_col]).sort_values(date_col)
            fig = go.Figure()
            for i, m in enumerate(selected):
                trend_df[m] = pd.to_numeric(trend_df[m], errors="coerce")
                fig.add_trace(go.Scatter(x=trend_df[date_col], y=trend_df[m], name=m,
                                         line=dict(color=COLORS[i % len(COLORS)], width=2.5),
                                         mode="lines+markers", marker=dict(size=5)))
            fig.update_layout(**chart_layout(f"{', '.join(selected)} Over Time", date_col, "Value"))
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ── Breakdown chart ───────────────────────────────────────────────────────────
cat_cols = [c for c in filtered_df.columns
            if filtered_df[c].dtype == object and c != date_col and filtered_df[c].nunique() <= 30]
if cat_cols and num_cols:
    st.markdown("#### Breakdown")
    col_l, col_r = st.columns(2)
    with col_l:
        group_by = st.selectbox("Group by", cat_cols)
    with col_r:
        metric = st.selectbox("Metric", [c for c in num_cols if c in filtered_df.columns])

    if group_by and metric:
        grouped = (filtered_df.groupby(group_by)[metric]
                   .apply(lambda s: pd.to_numeric(s, errors="coerce").sum())
                   .reset_index().sort_values(metric, ascending=False).head(15))
        fig2 = go.Figure(go.Bar(
            x=grouped[metric], y=grouped[group_by].astype(str).str[:40], orientation="h",
            marker_color=COLORS[0],
            text=grouped[metric].apply(lambda v: f"{v:,.0f}"),
            textposition="outside", textfont=dict(color="#1A1A2E"),
        ))
        layout2 = chart_layout(f"{metric} by {group_by}")
        layout2["yaxis"]["autorange"] = "reversed"
        fig2.update_layout(**layout2, height=max(300, len(grouped)*32))
        st.plotly_chart(fig2, use_container_width=True)

# ── Full data table ───────────────────────────────────────────────────────────
st.markdown("#### All Data")
st.markdown(f"**{len(filtered_df):,} rows**")
with st.expander("Show / Hide Table", expanded=True):
    st.dataframe(filtered_df, use_container_width=True, hide_index=True, height=400)

st.markdown("---")
col1, col2 = st.columns(2)
col1.caption(f"Google Sheet ID: `{sheet_id}`")
col2.caption(f"Total rows: {len(raw_df):,} · Filtered: {len(filtered_df):,} · Refreshed every 30 min")
