"""
Shared sidebar renderer.

Widget keys are DIFFERENT from session-state keys so that Streamlit's
internal widget-state mechanism never clobbers our stored values when
navigating between pages.  All persistent values live under their own
stable session-state keys (dark_mode, date_range_label, compare, etc.)
and are read/written explicitly around each widget call.
"""
import streamlit as st
from datetime import date, datetime, timedelta

_RANGE_OPTIONS = [
    "Last 7 days",
    "Last 30 days",
    "Last 90 days",
    "Year to date",
    "Last 12 months",
    "Custom",
]


def init_session_state() -> None:
    """Initialise all sidebar session-state keys with defaults (idempotent)."""
    defaults = {
        "dark_mode":        False,
        "date_range_label": "Last 30 days",
        "compare":          False,
        "custom_start":     None,
        "custom_end":       None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _compute_dates(label: str, today: date):
    """Return (start_date, end_date) for a named range label."""
    if label == "Last 7 days":
        return today - timedelta(days=7), today
    if label == "Last 30 days":
        return today - timedelta(days=30), today
    if label == "Last 90 days":
        return today - timedelta(days=90), today
    if label == "Year to date":
        return today.replace(month=1, day=1), today
    if label == "Last 12 months":
        return today - timedelta(days=365), today
    # Custom — values are written to session state by the widgets below
    start = st.session_state.get("custom_start") or today - timedelta(days=30)
    end   = st.session_state.get("custom_end")   or today
    return start, end


def _build_dict(start_date, end_date, compare: bool) -> dict:
    """Build the standard date-range return dict."""
    prior_start = prior_end = None
    if compare:
        period_len  = (end_date - start_date).days + 1
        prior_end   = start_date - timedelta(days=1)
        prior_start = prior_end - timedelta(days=period_len - 1)
    return {
        "start_date":      start_date,
        "end_date":        end_date,
        "prior_start":     prior_start,
        "prior_end":       prior_end,
        "compare_enabled": compare,
        "start_str":       start_date.strftime("%Y-%m-%d"),
        "end_str":         end_date.strftime("%Y-%m-%d"),
        "prior_start_str": prior_start.strftime("%Y-%m-%d") if prior_start else None,
        "prior_end_str":   prior_end.strftime("%Y-%m-%d")   if prior_end   else None,
    }


def get_date_range() -> dict:
    """
    Return the current date-range dict from session state without rendering
    any widgets.  Useful for pages that need dates before the sidebar runs.
    """
    init_session_state()
    today = datetime.today().date()
    start_date, end_date = _compute_dates(st.session_state["date_range_label"], today)
    return _build_dict(start_date, end_date, st.session_state["compare"])


def render_sidebar() -> dict:
    """
    Render the standard sidebar for every page and return the date-range dict.

    Returns
    -------
    dict with keys:
        start_date, end_date   – datetime.date objects
        prior_start, prior_end – datetime.date objects (None when compare off)
        compare_enabled        – bool
        start_str, end_str     – YYYY-MM-DD strings
        prior_start_str,
        prior_end_str          – YYYY-MM-DD strings or None
    """
    init_session_state()
    today = datetime.today().date()

    with st.sidebar:
        st.markdown("### 📊 Goodman Financial")
        st.markdown("---")

        # ── Dark mode ───────────────────────────────────────────────────────
        # Key "dm_toggle" is intentionally different from "dark_mode" so that
        # Streamlit's widget state doesn't overwrite our persisted value on
        # first render of a new page.
        dark = st.toggle(
            "🌙 Dark Mode",
            value=st.session_state["dark_mode"],
            key="dm_toggle",
        )
        st.session_state["dark_mode"] = dark
        st.markdown("---")

        # ── Date range ──────────────────────────────────────────────────────
        st.markdown("**Date Range**")
        idx = _RANGE_OPTIONS.index(st.session_state["date_range_label"])
        selected = st.selectbox(
            "Range", _RANGE_OPTIONS,
            index=idx, key="dr_select",
            label_visibility="collapsed",
        )
        st.session_state["date_range_label"] = selected

        if selected == "Custom":
            cs_default = st.session_state["custom_start"] or today - timedelta(days=30)
            ce_default = st.session_state["custom_end"]   or today
            start_date = st.date_input("Start", value=cs_default, key="cs_input")
            end_date   = st.date_input("End",   value=ce_default, key="ce_input")
            if end_date < start_date:
                st.error("End must be after start.")
                end_date = start_date
            st.session_state["custom_start"] = start_date
            st.session_state["custom_end"]   = end_date
        else:
            start_date, end_date = _compute_dates(selected, today)

        st.caption(f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}")
        st.markdown("---")

        # ── Compare toggle ──────────────────────────────────────────────────
        compare = st.checkbox(
            "Compare to previous period",
            value=st.session_state["compare"],
            key="cmp_checkbox",
        )
        st.session_state["compare"] = compare

        result = _build_dict(start_date, end_date, compare)

        if compare and result["prior_start"]:
            st.caption(
                f"vs. {result['prior_start'].strftime('%b %d')} – "
                f"{result['prior_end'].strftime('%b %d, %Y')}"
            )

        st.markdown("---")
        if st.button("Sign Out", use_container_width=True, key="signout_btn"):
            st.session_state["authenticated"] = False
            st.rerun()

    return result
