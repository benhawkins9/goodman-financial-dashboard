"""
Shared theme system — Goodman Financial Dashboard.
Provides theme dicts, CSS injection, KPI card, chart layout, and format helpers
used by every page.
"""
import streamlit as st

# ── Theme dicts ───────────────────────────────────────────────────────────────
LIGHT = {
    "bg":            "#F8F9FA",
    "card_bg":       "#FFFFFF",
    "card_border":   "#E2E8E4",
    "text_primary":  "#1A1A2E",
    "text_secondary":"#6B7280",
    "accent":        "#0F6E56",
    "accent_2":      "#1A9E7A",
    "negative":      "#C0392B",
    "chart_bg":      "#FFFFFF",
    "chart_plot_bg": "#FAFAFA",
    "chart_grid":    "#F0F0F0",
    "chart_line":    "#E2E8E4",
    "chart_font":    "#1A1A2E",
    "chart_axis":    "#6B7280",
    "fill_alpha":    "rgba(15,110,86,0.08)",
    "bar_fill":      "rgba(15,110,86,0.12)",
    "colors":        ["#0F6E56","#1A9E7A","#5BB89A","#8ECFC0","#3D8B70","#2A6B55"],
}

DARK = {
    "bg":            "#0F1A14",
    "card_bg":       "#1A2E22",
    "card_border":   "#2A4A35",
    "text_primary":  "#E8F5E9",
    "text_secondary":"#9AC89E",
    "accent":        "#4CAF50",
    "accent_2":      "#2DB896",
    "negative":      "#EF5350",
    "chart_bg":      "#1A2E22",
    "chart_plot_bg": "#0F1A14",
    "chart_grid":    "#2A4A35",
    "chart_line":    "#2A4A35",
    "chart_font":    "#E8F5E9",
    "chart_axis":    "#9AC89E",
    "fill_alpha":    "rgba(76,175,80,0.10)",
    "bar_fill":      "rgba(76,175,80,0.18)",
    "colors":        ["#4CAF50","#2DB896","#66BB6A","#81C784","#1A9E7A","#0F6E56"],
}


# ── Channel color map ─────────────────────────────────────────────────────────
# Consistent colors across every channel-based chart on every page.
CHANNEL_COLORS = {
    "Direct":          "#4CAF50",
    "Organic Search":  "#2196F3",
    "Referral":        "#FF9800",
    "Organic Social":  "#9C27B0",
    "Email":           "#00BCD4",
    "Paid Search":     "#F44336",
    "Paid Social":     "#E91E63",
    "Organic Video":   "#FF5722",
    "Organic Shopping":"#8BC34A",
    "Unassigned":      "#9E9E9E",
}

_CHANNEL_FALLBACKS = list(CHANNEL_COLORS.values())


def channel_color(channel: str, fallback_index: int = 0) -> str:
    """Return the canonical color for a GA4 channel group name."""
    return CHANNEL_COLORS.get(
        channel,
        _CHANNEL_FALLBACKS[fallback_index % len(_CHANNEL_FALLBACKS)],
    )


def get_theme() -> dict:
    """Return the active theme dict based on st.session_state['dark_mode']."""
    return DARK if st.session_state.get("dark_mode", False) else LIGHT


def apply_theme_css(theme: dict) -> None:
    """Inject full-page CSS from the active theme."""
    bg  = theme["bg"];  cbg = theme["card_bg"];  cbd = theme["card_border"]
    tp  = theme["text_primary"];  ts = theme["text_secondary"];  ac = theme["accent"]
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
#MainMenu,footer,header{{visibility:hidden;}}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main,.block-container{{background-color:{bg}!important;}}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] span{{color:{tp}!important;}}
.stCaption,[data-testid="stCaptionContainer"]{{color:{ts}!important;}}
label{{color:{ts}!important;}}
h1{{color:{tp}!important;font-weight:700;}}h2{{color:{tp}!important;font-weight:600;}}h3,h4{{color:{ac}!important;font-weight:600;}}
[data-testid="stSidebar"]{{background-color:#1C2B2B!important;}}
[data-testid="stSidebar"] *{{color:#E8F5E9!important;}}
[data-testid="stSidebar"] label{{color:#9AC89E!important;}}
[data-testid="stSidebar"] p{{color:#9AC89E!important;}}
[data-testid="stSidebar"] small{{color:#9AC89E!important;}}
[data-testid="stSidebar"] .stCaption{{color:#9AC89E!important;}}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{{color:#9AC89E!important;}}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{{color:#FFFFFF!important;}}
[data-testid="stSidebarNav"] a{{color:#E8F5E9!important;}}
[data-testid="stSidebarNav"] a:hover{{background-color:rgba(255,255,255,0.10)!important;color:#FFFFFF!important;}}
[data-testid="stSidebarNav"] a[aria-selected="true"]{{background-color:#0F6E56!important;border-left:3px solid #1A9E7A;}}
.stButton>button[kind="primary"]{{background-color:{ac}!important;border-color:{ac}!important;color:#FFFFFF!important;font-weight:600;border-radius:6px;}}
.stButton>button[kind="primary"]:hover{{background-color:{theme['accent_2']}!important;border-color:{theme['accent_2']}!important;}}
.stButton>button:not([kind="primary"]){{background-color:{cbg}!important;border-color:{cbd}!important;color:{tp}!important;border-radius:6px;}}
.stTabs [data-baseweb="tab-list"]{{background-color:transparent;border-bottom:2px solid {cbd};}}
.stTabs [data-baseweb="tab"]{{color:{ts}!important;}}
.stTabs [data-baseweb="tab"][aria-selected="true"]{{border-bottom:3px solid {ac}!important;color:{tp}!important;font-weight:600;}}
[data-testid="stDataFrame"]{{border:1px solid {cbd};border-radius:8px;background-color:{cbg}!important;}}
[data-testid="stAlert"]{{background-color:{cbg}!important;border-color:{cbd}!important;}}
[data-testid="stMetricValue"]{{color:{tp}!important;}}
[data-testid="stMetricLabel"]{{color:{ts}!important;}}
div[data-testid="metric-container"]{{background-color:{cbg};border:1px solid {cbd};border-radius:8px;padding:16px;}}
details[data-testid="stExpander"]{{background-color:{cbg}!important;border:1px solid {cbd}!important;border-radius:8px!important;}}
details[data-testid="stExpander"]>summary{{background-color:{cbg}!important;color:{tp}!important;}}
details[data-testid="stExpander"]>summary p,details[data-testid="stExpander"]>summary span,details[data-testid="stExpander"]>summary svg{{color:{tp}!important;fill:{tp}!important;}}
[data-testid="stExpanderDetails"]{{background-color:{cbg}!important;}}
hr{{border-color:{cbd}!important;}}
</style>""", unsafe_allow_html=True)


# ── Shared UI components ──────────────────────────────────────────────────────
def kpi_card(title: str, value: str, delta=None, muted: bool = False,
             lower_is_better: bool = False) -> str:
    """Return an HTML KPI card string using the active theme."""
    theme = get_theme()
    vc = theme["text_secondary"] if muted else theme["text_primary"]
    dh = ""
    if delta is not None:
        positive = (delta < 0) if lower_is_better else (delta >= 0)
        clr  = theme["accent"] if positive else theme["negative"]
        dh   = (f'<p style="color:{clr};font-size:12px;font-weight:500;margin:4px 0 0;">'
                f'{"▲" if delta >= 0 else "▼"} {abs(delta):.1f}%</p>')
    return (
        f'<div style="background:{theme["card_bg"]};border:1px solid {theme["card_border"]};'
        f'border-left:4px solid {theme["accent"]};border-radius:8px;padding:1.1rem 1.25rem;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.08);height:100%;">'
        f'<p style="color:{theme["text_secondary"]};font-size:11px;font-weight:500;'
        f'text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px;">{title}</p>'
        f'<h2 style="color:{vc};font-size:28px;font-weight:600;margin:0;line-height:1.1;">{value}</h2>'
        f'{dh}</div>'
    )


def chart_layout(title: str = "", xaxis_title: str = "", yaxis_title: str = "",
                 compact: bool = False) -> dict:
    """Return a Plotly layout dict using the active theme."""
    theme = get_theme()
    ax = dict(
        gridcolor=theme["chart_grid"], linecolor=theme["chart_line"],
        color=theme["chart_axis"], tickfont=dict(color=theme["chart_axis"]),
        title_font=dict(color=theme["chart_axis"]),
    )
    margin = dict(t=35, b=15, l=10, r=50) if compact else dict(t=50, b=40, l=50, r=20)
    return dict(
        title=dict(text=title, font=dict(size=15, color=theme["chart_font"]), x=0),
        plot_bgcolor=theme["chart_plot_bg"], paper_bgcolor=theme["chart_bg"],
        font=dict(family="Inter, sans-serif", color=theme["chart_font"]),
        xaxis=dict(title=xaxis_title, **ax),
        yaxis=dict(title=yaxis_title, **ax),
        margin=margin,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=theme["chart_font"])),
        hovermode="x unified",
    )


# ── Format helpers ────────────────────────────────────────────────────────────
def pct_delta(curr, prev):
    if prev is None or prev == 0 or curr is None:
        return None
    return ((curr - prev) / abs(prev)) * 100


def fmt_number(n):
    if n is None: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return f"{int(n):,}"


def fmt_currency(n):
    return f"${n:,.2f}" if n is not None else "—"


def fmt_pct(n):
    return f"{n:.2f}%" if n is not None else "—"


def fmt_duration(s):
    """Format seconds as Xm YYs."""
    m, sec = divmod(int(s), 60)
    return f"{m}m {sec:02d}s"
