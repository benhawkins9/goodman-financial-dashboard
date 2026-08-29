"""Goodman Financial data MCP server.

Exposes the dashboard's GA4 + Search Console connections as MCP tools,
reusing the same service-account credentials the Streamlit app uses.
Reads .streamlit/secrets.toml (same file/format as the app — copy it from
the Streamlit Cloud Secrets panel; it is gitignored).

Run: py mcp/server.py   (stdio transport)
"""
from __future__ import annotations

import tomllib
from pathlib import Path

from mcp.server import MCPServer

ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"

mcp = MCPServer(
    "goodman-dashboard",
    instructions="GA4 and Google Search Console data for goodmanfinancial.com, "
                 "via the same service account the Streamlit dashboard uses. "
                 "Call status first if a data tool errors.",
)


def _secrets() -> dict:
    if not SECRETS_PATH.exists():
        raise RuntimeError(
            f"Missing {SECRETS_PATH}. Copy the contents of the Streamlit Cloud "
            "Secrets panel (App -> Settings -> Secrets) into that file."
        )
    with SECRETS_PATH.open("rb") as f:
        return tomllib.load(f)


def _google_credentials(scopes: list[str]):
    from google.oauth2 import service_account

    s = _secrets()
    required = ["GA4_PROJECT_ID", "GA4_PRIVATE_KEY_ID", "GA4_PRIVATE_KEY",
                "GA4_CLIENT_EMAIL", "GA4_CLIENT_ID", "GA4_CLIENT_X509_CERT_URL"]
    missing = [k for k in required if not s.get(k)]
    if missing:
        raise RuntimeError(f"secrets.toml is missing: {', '.join(missing)}")
    creds_dict = {
        "type": "service_account",
        "project_id": s["GA4_PROJECT_ID"],
        "private_key_id": s["GA4_PRIVATE_KEY_ID"],
        "private_key": s["GA4_PRIVATE_KEY"].replace("\\n", "\n"),
        "client_email": s["GA4_CLIENT_EMAIL"],
        "client_id": s["GA4_CLIENT_ID"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": s["GA4_CLIENT_X509_CERT_URL"],
        "universe_domain": "googleapis.com",
    }
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)


@mcp.tool()
def status() -> dict:
    """Check which credentials are configured (never returns secret values)."""
    if not SECRETS_PATH.exists():
        return {"secrets_file": str(SECRETS_PATH), "exists": False,
                "fix": "Copy the Streamlit Cloud Secrets panel contents into this file."}
    s = _secrets()
    return {
        "secrets_file": str(SECRETS_PATH),
        "exists": True,
        "gsc_ready": bool(s.get("GSC_SITE_URL") and s.get("GA4_PRIVATE_KEY")),
        "ga4_ready": bool(s.get("GA4_PROPERTY_ID") and s.get("GA4_PRIVATE_KEY")),
        "gsc_site_url": s.get("GSC_SITE_URL", ""),
        "ga4_property_id": s.get("GA4_PROPERTY_ID", ""),
    }


@mcp.tool()
def gsc_search_analytics(start_date: str, end_date: str,
                         dimensions: list[str] | None = None,
                         row_limit: int = 100) -> list[dict]:
    """Query Google Search Console search analytics for goodmanfinancial.com.

    Args:
        start_date: YYYY-MM-DD (GSC data lags ~2 days behind today).
        end_date: YYYY-MM-DD.
        dimensions: any of query, page, date, country, device, searchAppearance.
            Omit/empty for overall totals. Multiple dimensions combine (e.g.
            ["query", "page"]).
        row_limit: max rows (1-25000).

    Returns rows with keys (dimension values), clicks, impressions, ctr_pct, position.
    """
    from googleapiclient.discovery import build

    s = _secrets()
    creds = _google_credentials(["https://www.googleapis.com/auth/webmasters.readonly"])
    service = build("searchconsole", "v1", credentials=creds)
    body = {"startDate": start_date, "endDate": end_date,
            "dimensions": dimensions or [], "rowLimit": max(1, min(row_limit, 25000))}
    resp = service.searchanalytics().query(siteUrl=s["GSC_SITE_URL"], body=body).execute()
    out = []
    for r in resp.get("rows", []):
        row = {d: k for d, k in zip(dimensions or [], r.get("keys", []))}
        row.update(clicks=int(r["clicks"]), impressions=int(r["impressions"]),
                   ctr_pct=round(r["ctr"] * 100, 2), position=round(r["position"], 1))
        out.append(row)
    return out


@mcp.tool()
def ga4_run_report(start_date: str, end_date: str,
                   metrics: list[str], dimensions: list[str] | None = None,
                   row_limit: int = 100) -> list[dict]:
    """Run a GA4 report for the Goodman Financial property.

    Args:
        start_date: YYYY-MM-DD (or e.g. "28daysAgo").
        end_date: YYYY-MM-DD (or "yesterday" / "today").
        metrics: GA4 API metric names, e.g. sessions, activeUsers, engagedSessions,
            engagementRate, keyEvents, eventCount, screenPageViews.
        dimensions: GA4 API dimension names, e.g. date, sessionDefaultChannelGroup,
            sessionSource, sessionMedium, landingPagePlusQueryString, pagePath.
        row_limit: max rows.

    Returns one dict per row: dimension values + metric values.
    """
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (DateRange, Dimension, Metric,
                                                    RunReportRequest)

    s = _secrets()
    creds = _google_credentials(["https://www.googleapis.com/auth/analytics.readonly"])
    client = BetaAnalyticsDataClient(credentials=creds)
    req = RunReportRequest(
        property=f"properties/{s['GA4_PROPERTY_ID']}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        metrics=[Metric(name=m) for m in metrics],
        dimensions=[Dimension(name=d) for d in (dimensions or [])],
        limit=max(1, row_limit),
    )
    resp = client.run_report(req)
    dim_names = [d.name for d in resp.dimension_headers]
    met_names = [m.name for m in resp.metric_headers]
    out = []
    for r in resp.rows:
        row = {n: v.value for n, v in zip(dim_names, r.dimension_values)}
        row.update({n: v.value for n, v in zip(met_names, r.metric_values)})
        out.append(row)
    return out


if __name__ == "__main__":
    mcp.run()
