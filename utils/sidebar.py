"""
Shared sidebar renderer — persists date range, compare toggle, and dark mode in
st.session_state so selections survive page navigation.
"""
import streamlit as st
from datetime import datetime, timedelta

RANGE_OPTIONS = [
    "Last 7 days",
    "Last 30 days",
    "Last 90 days",
    "Year to date",
    "Last 12 months",
    "Custom",
]


def init_session_state() -> None:
    """Initialise all sidebar session-state keys with defaults (idempotent)."""
    today = datetime.today().date()
    st.session_state.setdefault("dark_mode",         False)
    st.session_state.setdefault("date_range_opt",    "Last 30 days")
    st.session_state.setdefault("compare_enabled",   False)
    st.session_state.setdefault("custom_start_date", today - timedelta(days=30))
    st.session_state.setdefault("custom_end_date",   today)


def _compute_dates(opt: str, today) -> tuple:
    """Return (start_date, end_date) for a named range option."""
    if opt == "Last 7 days":
        return today - timedelta(days=7), today
    if opt == "Last 30 days":
        return today - timedelta(days=30), today
    if opt == "Last 90 days":
        return today - timedelta(days=90), today
    if opt == "Year to date":
        return today.replace(month=1, day=1), today
    if opt == "Last 12 months":
        return today - timedelta(days=365), today
    # Custom — caller must set session state keys
    start = st.session_state.get("custom_start_date") or today - timedelta(days=30)
    end   = st.session_state.get("custom_end_date")   or today
    return start, end


def get_date_range() -> dict:
    """
    Return the current date-range dict from session state without re-rendering
    the sidebar.  Useful for pages that only need the date values.

    Returns the same keys as render_sidebar().
    """
    init_session_state()
    today = datetime.today().date()
    start_date, end_date = _compute_dates(
        st.session_state["date_range_opt"], today
    )
    compare_enabled = st.session_state.get("compare_enabled", False)
    prior_start = prior_end = None
    if compare_enabled:
        period_len  = (end_date - start_date).days + 1
        prior_end   = start_date - timedelta(days=1)
        prior_start = prior_end - timedelta(days=period_len - 1)
    return {
        "start_date":      start_date,
        "end_date":        end_date,
        "prior_start":     prior_start,
        "prior_end":       prior_end,
        "compare_enabled": compare_enabled,
        "start_str":       start_date.strftime("%Y-%m-%d"),
        "end_str":         end_date.strftime("%Y-%m-%d"),
        "prior_start_str": prior_start.strftime("%Y-%m-%d") if prior_start else None,
        "prior_end_str":   prior_end.strftime("%Y-%m-%d")   if prior_end   else None,
    }


def render_sidebar() -> dict:
    """
    Renders the standard sidebar for every page.

    Returns
    -------
    dict with keys:
        start_date, end_date   – datetime.date objects for the selected period
        prior_start, prior_end – datetime.date objects for the prior period
                                 (both None when compare is disabled)
        compare_enabled        – bool
        start_str, end_str     – YYYY-MM-DD strings (convenience)
        prior_start_str,
        prior_end_str          – YYYY-MM-DD strings or None
    """
    today = datetime.today().date()
    init_session_state()

    with st.sidebar:
        st.markdown("### 📊 Goodman Financial")
        st.markdown("---")

        # ── Dark / light mode toggle ────────────────────────────────────────
        st.toggle("🌙 Dark Mode", key="dark_mode")
        st.markdown("---")

        # ── Date range ──────────────────────────────────────────────────────
        st.markdown("**Date Range**")

        range_opt = st.selectbox(
            "Range",
            RANGE_OPTIONS,
            key="date_range_opt",
            label_visibility="collapsed",
        )

        if range_opt == "Custom":
            start_date = st.date_input("Start", key="custom_start_date")
            end_date   = st.date_input("End",   key="custom_end_date")
            if end_date < start_date:
                st.error("End must be after start.")
                end_date = start_date
        else:
            start_date, end_date = _compute_dates(range_opt, today)

        st.caption(f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}")
        st.markdown("---")

        compare_enabled = st.checkbox(
            "Compare to previous period",
            key="compare_enabled",
        )

        prior_start = prior_end = None
        if compare_enabled:
            period_len  = (end_date - start_date).days + 1
            prior_end   = start_date - timedelta(days=1)
            prior_start = prior_end - timedelta(days=period_len - 1)
            st.caption(
                f"vs. {prior_start.strftime('%b %d')} – {prior_end.strftime('%b %d, %Y')}"
            )

        st.markdown("---")
        if st.button("Sign Out", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    return {
        "start_date":      start_date,
        "end_date":        end_date,
        "prior_start":     prior_start,
        "prior_end":       prior_end,
        "compare_enabled": compare_enabled,
        "start_str":       start_date.strftime("%Y-%m-%d"),
        "end_str":         end_date.strftime("%Y-%m-%d"),
        "prior_start_str": prior_start.strftime("%Y-%m-%d") if prior_start else None,
        "prior_end_str":   prior_end.strftime("%Y-%m-%d")   if prior_end   else None,
    }
