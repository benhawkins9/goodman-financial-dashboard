import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd


st.set_page_config(
    page_title="LinkedIn — Goodman Financial",
    page_icon="💼",
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

def kpi_card(title, value):
    return f"""<div style="background:#F4FBF8;border:1px solid #D4EDE5;border-left:4px solid #0F6E56;
                border-radius:8px;padding:1.1rem 1.25rem;">
        <p style="color:#6B7280;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 6px;">{title}</p>
        <h2 style="color:#0F2A22;font-size:1.7rem;font-weight:700;margin:0;">{value}</h2>
    </div>"""

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

# Known column name variants → canonical names
COLUMN_MAP = {
    # Impressions
    "impressions": "Impressions",
    "impression": "Impressions",
    "total impressions": "Impressions",
    # Clicks
    "clicks": "Clicks",
    "click": "Clicks",
    "link clicks": "Clicks",
    # CTR
    "ctr": "CTR (%)",
    "click-through rate": "CTR (%)",
    "click through rate": "CTR (%)",
    # Spend
    "spend": "Spend ($)",
    "amount spent": "Spend ($)",
    "cost": "Spend ($)",
    # Engagements
    "engagements": "Engagements",
    "total engagements": "Engagements",
    "engagement": "Engagements",
    # Followers
    "followers": "Followers",
    "new followers": "New Followers",
    # Date
    "date": "Date",
    "week": "Week",
    "month": "Month",
    "period": "Period",
    # Conversions / leads
    "conversions": "Conversions",
    "leads": "Leads",
    "form submissions": "Leads",
}


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
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.get_worksheet(0)
    records = ws.get_all_records()
    return pd.DataFrame(records)


def normalise_df(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to canonical names using COLUMN_MAP (case-insensitive)."""
    rename = {}
    for col in df.columns:
        canonical = COLUMN_MAP.get(col.strip().lower())
        if canonical and canonical not in df.columns:
            rename[col] = canonical
    return df.rename(columns=rename)


def try_date_col(df: pd.DataFrame) -> str | None:
    """Return the name of the first date-like column, or None."""
    for candidate in ["Date", "Week", "Month", "Period"]:
        if candidate in df.columns:
            return candidate
    return None


def numeric_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown("## LinkedIn")
st.markdown(f"**{start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}**")
st.markdown("---")

try:
    sheet_id = st.secrets["LINKEDIN_SHEET_ID"]
    _project_id = st.secrets["GA4_PROJECT_ID"]
    _private_key_id = st.secrets["GA4_PRIVATE_KEY_ID"]
    _private_key = st.secrets["GA4_PRIVATE_KEY"]
    _client_email = st.secrets["GA4_CLIENT_EMAIL"]
    _client_id = st.secrets["GA4_CLIENT_ID"]
    _client_x509_cert_url = st.secrets["GA4_CLIENT_X509_CERT_URL"]
except KeyError as e:
    st.error(f"Missing secret: {e}. Add LINKEDIN_SHEET_ID and all GA4_* secrets to secrets.toml.")
    st.stop()

with st.spinner("Loading LinkedIn data from Google Sheet…"):
    try:
        raw_df = fetch_sheet(sheet_id, _project_id, _private_key_id, _private_key,
                             _client_email, _client_id, _client_x509_cert_url)
    except Exception as e:
        st.error(f"Could not load Google Sheet: {e}")
        st.info(f"Make sure the sheet is shared with your service account email ({_client_email}).")
        st.stop()

if raw_df.empty:
    st.warning("The Google Sheet appears to be empty.")
    st.stop()

df = normalise_df(raw_df)

# ── Date filtering ──
date_col = try_date_col(df)
filtered_df = df.copy()
if date_col:
    try:
        filtered_df[date_col] = pd.to_datetime(filtered_df[date_col], infer_datetime_format=True, errors="coerce")
        mask = (filtered_df[date_col].dt.date >= start_date) & (filtered_df[date_col].dt.date <= end_date)
        filtered_df = filtered_df[mask]
        if filtered_df.empty:
            st.warning("No data in the selected date range. Showing all rows.")
            filtered_df = df.copy()
    except Exception:
        pass

num_cols = numeric_cols(filtered_df)

# ── KPI Cards ──
PRIORITY_KPIS = ["Impressions", "Clicks", "Engagements", "Spend ($)", "CTR (%)", "Conversions", "Leads", "Followers", "New Followers"]
kpi_cols_to_show = [c for c in PRIORITY_KPIS if c in filtered_df.columns]

# Fall back to any numeric columns if none of the priority ones are present
if not kpi_cols_to_show:
    kpi_cols_to_show = num_cols[:6]

if kpi_cols_to_show:
    card_cols = st.columns(min(len(kpi_cols_to_show), 4))
    for i, col_name in enumerate(kpi_cols_to_show[:4]):
        total = pd.to_numeric(filtered_df[col_name], errors="coerce").sum()
        if "($)" in col_name or "spend" in col_name.lower() or "cost" in col_name.lower():
            display = f"${total:,.2f}"
        elif "(%)" in col_name or "rate" in col_name.lower() or "ctr" in col_name.lower():
            display = f"{total:.2f}%"
        else:
            display = f"{total:,.0f}" if total == int(total) else f"{total:,.2f}"
        card_cols[i].markdown(kpi_card(col_name, display), unsafe_allow_html=True)

    if len(kpi_cols_to_show) > 4:
        card_cols2 = st.columns(min(len(kpi_cols_to_show) - 4, 4))
        for i, col_name in enumerate(kpi_cols_to_show[4:8]):
            total = pd.to_numeric(filtered_df[col_name], errors="coerce").sum()
            if "($)" in col_name:
                display = f"${total:,.2f}"
            elif "(%)" in col_name:
                display = f"{total:.2f}%"
            else:
                display = f"{total:,.0f}" if total == int(total) else f"{total:,.2f}"
            card_cols2[i].markdown(kpi_card(col_name, display), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts ──
if date_col and date_col in filtered_df.columns and len(num_cols) > 0:
    chart_candidates = [c for c in ["Impressions", "Clicks", "Engagements"] if c in filtered_df.columns]
    if not chart_candidates:
        chart_candidates = num_cols[:3]

    if chart_candidates:
        st.markdown("#### Trend Over Time")
        selected_metrics = st.multiselect(
            "Select metrics to plot",
            options=chart_candidates,
            default=chart_candidates[:2],
        )

        if selected_metrics:
            trend_df = filtered_df[[date_col] + selected_metrics].copy()
            trend_df = trend_df.dropna(subset=[date_col])
            trend_df = trend_df.sort_values(date_col)

            fig = go.Figure()
            for i, metric in enumerate(selected_metrics):
                trend_df[metric] = pd.to_numeric(trend_df[metric], errors="coerce")
                fig.add_trace(go.Scatter(
                    x=trend_df[date_col],
                    y=trend_df[metric],
                    name=metric,
                    line=dict(color=COLORS[i % len(COLORS)], width=2.5),
                    mode="lines+markers",
                    marker=dict(size=5),
                ))
            fig.update_layout(**chart_layout(f"{', '.join(selected_metrics)} Over Time", date_col, "Value"))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ── Distribution chart (if a categorical column exists) ──
cat_cols = [c for c in filtered_df.columns if filtered_df[c].dtype == object and c != date_col and filtered_df[c].nunique() <= 30]
if cat_cols and num_cols:
    st.markdown("#### Breakdown")
    col_left, col_right = st.columns(2)

    with col_left:
        group_by = st.selectbox("Group by", cat_cols, key="group_by")
    with col_right:
        metric = st.selectbox("Metric", [c for c in num_cols if c in filtered_df.columns], key="metric")

    if group_by and metric:
        grouped = (
            filtered_df.groupby(group_by)[metric]
            .apply(lambda s: pd.to_numeric(s, errors="coerce").sum())
            .reset_index()
            .sort_values(metric, ascending=False)
            .head(15)
        )
        fig2 = go.Figure(go.Bar(
            x=grouped[metric],
            y=grouped[group_by].astype(str).str[:40],
            orientation="h",
            marker_color=COLORS[0],
            text=grouped[metric].apply(lambda v: f"{v:,.0f}"),
            textposition="outside",
        ))
        fig2.update_layout(**chart_layout(f"{metric} by {group_by}"))
        fig2.update_layout(yaxis=dict(autorange="reversed"), height=max(300, len(grouped) * 32))
        st.plotly_chart(fig2, use_container_width=True)

# ── Full data table ──
st.markdown("#### All Data")
st.markdown(f"**{len(filtered_df):,} rows** from Google Sheet")

with st.expander("Show / Hide Table", expanded=True):
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# ── Sheet info ──
st.markdown("---")
col1, col2 = st.columns(2)
col1.caption(f"Google Sheet ID: `{sheet_id}`")
col2.caption(f"Total rows loaded: {len(raw_df):,} · Filtered: {len(filtered_df):,} · Refreshed every 30 min")
