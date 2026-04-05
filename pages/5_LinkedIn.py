import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="LinkedIn — Goodman Financial", page_icon="💼",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main,.block-container{background-color:#0F1A14!important;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] span{color:#E8F5E9!important;}
.stCaption,[data-testid="stCaptionContainer"]{color:#9AC89E!important;}
label{color:#9AC89E!important;}
h1{color:#E8F5E9!important;font-weight:700;}h2{color:#E8F5E9!important;font-weight:600;}h3,h4{color:#9AC89E!important;font-weight:600;}
[data-testid="stSidebar"]{background-color:#0F6E56!important;}
[data-testid="stSidebar"] *{color:rgba(255,255,255,0.92)!important;}
[data-testid="stSidebarNav"] a[aria-selected="true"]{background-color:rgba(255,255,255,0.18)!important;border-left:3px solid white;}
.stButton>button[kind="primary"]{background-color:#4CAF50!important;border-color:#4CAF50!important;color:#0F1A14!important;font-weight:700;border-radius:6px;}
.stButton>button:not([kind="primary"]){background-color:#1A2E22!important;border-color:#2A4A35!important;color:#E8F5E9!important;border-radius:6px;}
.stTabs [data-baseweb="tab-list"]{background-color:transparent;border-bottom:2px solid #2A4A35;}
.stTabs [data-baseweb="tab"]{color:#9AC89E!important;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{border-bottom:3px solid #4CAF50!important;color:#E8F5E9!important;font-weight:600;}
[data-testid="stDataFrame"]{border:1px solid #2A4A35;border-radius:8px;}
[data-testid="stAlert"]{background-color:#1A2E22!important;border-color:#2A4A35!important;}
hr{border-color:#2A4A35!important;}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

COLORS = ["#4CAF50", "#2DB896", "#66BB6A", "#81C784", "#1A9E7A", "#0F6E56"]

def kpi_card(title, value):
    return f"""<div style="background:#1A2E22;border:1px solid #2A4A35;border-left:4px solid #4CAF50;
                border-radius:8px;padding:1.1rem 1.25rem;">
        <p style="color:#9AC89E;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 6px;">{title}</p>
        <h2 style="color:#4CAF50;font-size:1.7rem;font-weight:700;margin:0;">{value}</h2>
    </div>"""

def chart_layout(title="", xaxis_title="", yaxis_title=""):
    return dict(
        title=dict(text=title, font=dict(size=15, color="#E8F5E9"), x=0),
        plot_bgcolor="#0F1A14", paper_bgcolor="#0F1A14",
        font=dict(family="Inter, sans-serif", color="#E8F5E9"),
        xaxis=dict(title=xaxis_title, gridcolor="#1A2E22", linecolor="#2A4A35",
                   color="#9AC89E", tickfont=dict(color="#9AC89E"), title_font=dict(color="#9AC89E")),
        yaxis=dict(title=yaxis_title, gridcolor="#1A2E22", linecolor="#2A4A35",
                   color="#9AC89E", tickfont=dict(color="#9AC89E"), title_font=dict(color="#9AC89E")),
        margin=dict(t=50, b=40, l=50, r=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#E8F5E9")),
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

with st.sidebar:
    st.markdown("### 📊 Goodman Financial")
    st.markdown("---")
    st.markdown("**Date Range**")
    range_opt = st.selectbox("Range", ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
                             index=1, label_visibility="collapsed")
    today = datetime.today().date()
    if range_opt == "Last 7 days":     start_date, end_date = today - timedelta(days=7), today
    elif range_opt == "Last 30 days":  start_date, end_date = today - timedelta(days=30), today
    elif range_opt == "Last 90 days":  start_date, end_date = today - timedelta(days=90), today
    else:
        start_date = st.date_input("Start", value=today - timedelta(days=30))
        end_date   = st.date_input("End",   value=today)
    st.caption(f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}")
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()


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
    sheet_id            = st.secrets["LINKEDIN_SHEET_ID"]
    _project_id         = st.secrets["GA4_PROJECT_ID"]
    _private_key_id     = st.secrets["GA4_PRIVATE_KEY_ID"]
    _private_key        = st.secrets["GA4_PRIVATE_KEY"]
    _client_email       = st.secrets["GA4_CLIENT_EMAIL"]
    _client_id          = st.secrets["GA4_CLIENT_ID"]
    _client_x509        = st.secrets["GA4_CLIENT_X509_CERT_URL"]
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
            textposition="outside", textfont=dict(color="#E8F5E9"),
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
