import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.sidebar import render_sidebar
from utils.theme import get_theme, apply_theme_css

import streamlit as st

st.set_page_config(page_title="Google Ads — Goodman Financial", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")

if not st.session_state.get("authenticated"):
    st.warning("Please sign in from the **Overview** page.")
    st.stop()

render_sidebar()

theme = get_theme()
apply_theme_css(theme)

st.markdown("## Google Ads")
st.markdown("---")

st.markdown(f"""
<div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-left:5px solid #D4A017;
            border-radius:10px;padding:2rem 2.5rem;max-width:720px;margin:2rem auto;
            box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <span style="font-size:1.8rem;">🔑</span>
        <h2 style="color:{theme['text_primary']};margin:0;font-size:1.3rem;font-weight:700;">Google Ads Credentials Pending</h2>
    </div>
    <p style="color:{theme['text_primary']};margin:0 0 1rem;line-height:1.6;">
        This page is ready to display Google Ads campaign data once credentials are added to
        <code style="background:{theme['bg']};padding:1px 5px;border-radius:3px;color:{theme['accent']};border:1px solid {theme['card_border']};">secrets.toml</code>.
    </p>
    <hr style="border-color:{theme['card_border']};margin:1.25rem 0;">
    <h3 style="color:{theme['accent']};font-size:1rem;margin:0 0 0.75rem;">Steps to connect Google Ads</h3>
    <ol style="color:{theme['text_primary']};line-height:1.9;margin:0;padding-left:1.3rem;">
        <li><strong style="color:{theme['accent']};">Developer token</strong> — Apply in your Google Ads Manager Account under
            <em>Tools &amp; Settings → API Center</em>.</li>
        <li><strong style="color:{theme['accent']};">OAuth 2.0 credentials</strong> — Create a <em>Desktop app</em> OAuth client
            in Google Cloud Console. Download the client JSON.</li>
        <li><strong style="color:{theme['accent']};">Refresh token</strong> — Run the Google Ads Python OAuth flow
            (<code style="color:{theme['accent']};">python generate_refresh_token.py</code>) to obtain a long-lived token.</li>
        <li><strong style="color:{theme['accent']};">Customer ID</strong> — Found in the top-right of Google Ads UI (format: 123-456-7890).</li>
        <li><strong style="color:{theme['accent']};">Add to secrets.toml</strong> — Uncomment the <code style="color:{theme['accent']};">GOOGLE_ADS_*</code> keys.</li>
    </ol>
    <hr style="border-color:{theme['card_border']};margin:1.25rem 0;">
    <pre style="background:{theme['bg']};border:1px solid {theme['card_border']};border-radius:6px;padding:1rem;
                font-size:0.85rem;color:{theme['accent']};overflow-x:auto;margin:0;">
GOOGLE_ADS_DEVELOPER_TOKEN  = "your-developer-token"
GOOGLE_ADS_CLIENT_ID        = "000000000000-xxxxx.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET    = "GOCSPX-xxxxxxxxxxxxxxxxxxxx"
GOOGLE_ADS_REFRESH_TOKEN    = "1//0xxxxxxxxxxxxxxxxxxxxxxxx"
GOOGLE_ADS_CUSTOMER_ID      = "123-456-7890"</pre>
    <hr style="border-color:{theme['card_border']};margin:1.25rem 0;">
    <p style="color:{theme['text_secondary']};font-size:0.85rem;margin:0;">
        <strong>Required package:</strong>
        <code style="background:{theme['bg']};padding:1px 5px;border-radius:3px;color:{theme['accent']};border:1px solid {theme['card_border']};">google-ads&gt;=23.0.0</code>
        — add to <code style="color:{theme['accent']};">requirements.txt</code> and re-install before enabling.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("#### What you'll see once connected")
preview_cols = st.columns(5)
for col, label in zip(preview_cols, ["Spend", "Impressions", "Clicks", "CTR", "Conv. Rate"]):
    col.markdown(f"""
    <div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-left:4px solid {theme['card_border']};
                border-radius:8px;padding:1.1rem 1.25rem;opacity:0.5;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <p style="color:{theme['text_secondary']};font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px;">{label}</p>
        <h2 style="color:{theme['card_border']};font-size:28px;font-weight:600;margin:0;">—</h2>
    </div>""", unsafe_allow_html=True)

st.markdown("---")
st.caption("Google Ads · Credentials not yet configured")
