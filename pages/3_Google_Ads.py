import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Google Ads — Goodman Financial",
    page_icon="🎯",
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
h1,h2{color:#0F6E56!important;font-weight:700;}
hr{border-color:#E0EDE9!important;}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

with st.sidebar:
    st.markdown("### 📊 Goodman Financial")
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown("## Google Ads")
st.markdown("---")

# ── Pending credentials card ──
st.markdown("""
<div style="
    background: #FFFBEA;
    border: 1px solid #F5C842;
    border-left: 5px solid #F5C842;
    border-radius: 10px;
    padding: 2rem 2.5rem;
    max-width: 720px;
    margin: 2rem auto;
">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <span style="font-size:1.8rem;">🔑</span>
        <h2 style="color:#7A5C00;margin:0;font-size:1.3rem;font-weight:700;">Google Ads Credentials Pending</h2>
    </div>
    <p style="color:#6B5700;margin:0 0 1rem;line-height:1.6;">
        This page is ready to display Google Ads campaign data once credentials are added to
        <code style="background:#FEF3CD;padding:1px 5px;border-radius:3px;">secrets.toml</code>.
    </p>
    <hr style="border-color:#F0D080;margin:1.25rem 0;">
    <h3 style="color:#7A5C00;font-size:1rem;margin:0 0 0.75rem;">Steps to connect Google Ads</h3>
    <ol style="color:#5C4500;line-height:1.9;margin:0;padding-left:1.3rem;">
        <li>
            <strong>Developer token</strong> — Apply in your Google Ads Manager Account under
            <em>Tools &amp; Settings → API Center</em>. Copy the token once approved.
        </li>
        <li>
            <strong>OAuth 2.0 credentials</strong> — Create a <em>Desktop app</em> OAuth client in
            Google Cloud Console for your project. Download the client JSON.
        </li>
        <li>
            <strong>Refresh token</strong> — Run the Google Ads Python client OAuth flow
            (<code>python generate_refresh_token.py</code>) to obtain a long-lived refresh token.
        </li>
        <li>
            <strong>Customer ID</strong> — Find it in the top-right of Google Ads UI (format: 123-456-7890).
        </li>
        <li>
            <strong>Add to <code>secrets.toml</code></strong> — Uncomment and fill in the
            <code>GOOGLE_ADS_*</code> keys shown in the template.
        </li>
    </ol>
    <hr style="border-color:#F0D080;margin:1.25rem 0;">
    <h3 style="color:#7A5C00;font-size:1rem;margin:0 0 0.75rem;">Add these keys to <code>.streamlit/secrets.toml</code></h3>
    <pre style="background:#FEF9E7;border:1px solid #F0D080;border-radius:6px;padding:1rem;
                font-size:0.85rem;color:#5C4500;overflow-x:auto;margin:0;">
GOOGLE_ADS_DEVELOPER_TOKEN  = "your-developer-token"
GOOGLE_ADS_CLIENT_ID        = "000000000000-xxxxx.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET    = "GOCSPX-xxxxxxxxxxxxxxxxxxxx"
GOOGLE_ADS_REFRESH_TOKEN    = "1//0xxxxxxxxxxxxxxxxxxxxxxxx"
GOOGLE_ADS_CUSTOMER_ID      = "123-456-7890"   # without dashes also works</pre>
    <hr style="border-color:#F0D080;margin:1.25rem 0;">
    <p style="color:#7A5C00;font-size:0.85rem;margin:0;">
        <strong>Required package:</strong>
        <code style="background:#FEF3CD;padding:1px 5px;border-radius:3px;">google-ads>=23.0.0</code>
        — add to <code>requirements.txt</code> and re-install before enabling.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Preview of what will be shown ──
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("#### What you'll see once connected")

preview_cols = st.columns(5)
placeholders = [
    ("Spend", "$—"),
    ("Impressions", "—"),
    ("Clicks", "—"),
    ("CTR", "—%"),
    ("Conv. Rate", "—%"),
]
for col, (label, val) in zip(preview_cols, placeholders):
    col.markdown(f"""
    <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-left:4px solid #D1D5DB;
                border-radius:8px;padding:1.1rem 1.25rem;opacity:0.6;">
        <p style="color:#9CA3AF;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 6px;">{label}</p>
        <h2 style="color:#D1D5DB;font-size:1.7rem;font-weight:700;margin:0;">{val}</h2>
    </div>""", unsafe_allow_html=True)

st.markdown("---")
st.caption("Google Ads · Credentials not yet configured")
