from typing import Any
from langchain_core.tools import tool


@tool
def get_workspace_stats(organization_id: int) -> dict[str, Any]:
    """Get the overall security statistics for the organization's workspace.
    
    Returns counts of apps, users, and risk distribution.
    """
    return {
        "ui_hint": "chart:pie",
        "data": {
            "total_apps": 12,
            "high_risk_apps": 2,
            "medium_risk_apps": 5,
            "low_risk_apps": 5,
            "total_users": 150,
        },
    }


@tool
def list_apps(organization_id: int, risk_level: str | None = None) -> dict[str, Any]:
    """List all monitored SaaS applications for the organization.
    
    Can optionally filter by risk_level (high, medium, low).
    """
    return {
        "ui_hint": "table:apps",
        "data": [
            {"id": 1, "name": "Microsoft 365", "risk": "medium", "users": 120},
            {"id": 2, "name": "Salesforce", "risk": "high", "users": 45},
            {"id": 3, "name": "Slack", "risk": "low", "users": 150},
        ],
    }


@tool
def get_app_details(app_id: int) -> dict[str, Any]:
    """Get detailed security analysis for a specific SaaS application."""
    return {
        "ui_hint": "card:app_detail",
        "data": {
            "id": app_id,
            "name": "Salesforce",
            "risk_level": "high",
            "scopes_granted": ["read:users", "write:opportunities", "admin:reports"],
            "last_scan": "2025-12-25T18:00:00Z",
            "findings": 3,
        },
    }
