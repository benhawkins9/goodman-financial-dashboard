import streamlit as st

st.set_page_config(page_title="Google Ads — Goodman Financial", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main,.block-container{background-color:#0F1A14!important;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] span{color:#E8F5E9!important;}
label{color:#9AC89E!important;}
h1{color:#E8F5E9!important;font-weight:700;}h2{color:#E8F5E9!important;font-weight:600;}h3,h4{color:#9AC89E!important;}
[data-testid="stSidebar"]{background-color:#0F6E56!important;}
[data-testid="stSidebar"] *{color:rgba(255,255,255,0.92)!important;}
[data-testid="stSidebarNav"] a[aria-selected="true"]{background-color:rgba(255,255,255,0.18)!important;border-left:3px solid white;}
.stButton>button:not([kind="primary"]){background-color:#1A2E22!important;border-color:#2A4A35!important;color:#E8F5E9!important;border-radius:6px;}
hr{border-color:#2A4A35!important;}
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

st.markdown("## Google Ads")
st.markdown("---")

st.markdown("""
<div style="background:#1A2E22;border:1px solid #2A4A35;border-left:5px solid #F5C842;
            border-radius:10px;padding:2rem 2.5rem;max-width:720px;margin:2rem auto;">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <span style="font-size:1.8rem;">🔑</span>
        <h2 style="color:#F5E642;margin:0;font-size:1.3rem;font-weight:700;">Google Ads Credentials Pending</h2>
    </div>
    <p style="color:#E8F5E9;margin:0 0 1rem;line-height:1.6;">
        This page is ready to display Google Ads campaign data once credentials are added to
        <code style="background:#0F1A14;padding:1px 5px;border-radius:3px;color:#4CAF50;">secrets.toml</code>.
    </p>
    <hr style="border-color:#2A4A35;margin:1.25rem 0;">
    <h3 style="color:#9AC89E;font-size:1rem;margin:0 0 0.75rem;">Steps to connect Google Ads</h3>
    <ol style="color:#E8F5E9;line-height:1.9;margin:0;padding-left:1.3rem;">
        <li><strong style="color:#4CAF50;">Developer token</strong> — Apply in your Google Ads Manager Account under
            <em>Tools &amp; Settings → API Center</em>.</li>
        <li><strong style="color:#4CAF50;">OAuth 2.0 credentials</strong> — Create a <em>Desktop app</em> OAuth client
            in Google Cloud Console. Download the client JSON.</li>
        <li><strong style="color:#4CAF50;">Refresh token</strong> — Run the Google Ads Python OAuth flow
            (<code style="color:#4CAF50;">python generate_refresh_token.py</code>) to obtain a long-lived token.</li>
        <li><strong style="color:#4CAF50;">Customer ID</strong> — Found in the top-right of Google Ads UI (format: 123-456-7890).</li>
        <li><strong style="color:#4CAF50;">Add to secrets.toml</strong> — Uncomment the <code style="color:#4CAF50;">GOOGLE_ADS_*</code> keys.</li>
    </ol>
    <hr style="border-color:#2A4A35;margin:1.25rem 0;">
    <pre style="background:#0F1A14;border:1px solid #2A4A35;border-radius:6px;padding:1rem;
                font-size:0.85rem;color:#4CAF50;overflow-x:auto;margin:0;">
GOOGLE_ADS_DEVELOPER_TOKEN  = "your-developer-token"
GOOGLE_ADS_CLIENT_ID        = "000000000000-xxxxx.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET    = "GOCSPX-xxxxxxxxxxxxxxxxxxxx"
GOOGLE_ADS_REFRESH_TOKEN    = "1//0xxxxxxxxxxxxxxxxxxxxxxxx"
GOOGLE_ADS_CUSTOMER_ID      = "123-456-7890"</pre>
    <hr style="border-color:#2A4A35;margin:1.25rem 0;">
    <p style="color:#9AC89E;font-size:0.85rem;margin:0;">
        <strong>Required package:</strong>
        <code style="background:#0F1A14;padding:1px 5px;border-radius:3px;color:#4CAF50;">google-ads&gt;=23.0.0</code>
        — add to <code style="color:#4CAF50;">requirements.txt</code> and re-install before enabling.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("#### What you'll see once connected")
preview_cols = st.columns(5)
for col, label in zip(preview_cols, ["Spend", "Impressions", "Clicks", "CTR", "Conv. Rate"]):
    col.markdown(f"""
    <div style="background:#1A2E22;border:1px solid #2A4A35;border-left:4px solid #2A4A35;
                border-radius:8px;padding:1.1rem 1.25rem;opacity:0.5;">
        <p style="color:#9AC89E;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 6px;">{label}</p>
        <h2 style="color:#2A4A35;font-size:1.7rem;font-weight:700;margin:0;">—</h2>
    </div>""", unsafe_allow_html=True)

st.markdown("---")
st.caption("Google Ads · Credentials not yet configured")
