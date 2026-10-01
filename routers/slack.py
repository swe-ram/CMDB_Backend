
from typing import Any

from fastapi import APIRouter

from config.settings import get_settings
from services.inventory_service import (
    build_inventory_payload,
    get_optimization_recommendations,
)
from services.slack_client import SlackClient
from services.slack_license import get_license_data, get_slack_license_info
from services.slack_usage import get_usage_summary
from services.slack_users import get_user_mapping, list_slack_users
from services.slack_workspace import get_workspace_info

router = APIRouter(prefix="/slack", tags=["Slack"])


def _build_client() -> SlackClient:
    settings = get_settings()
    return SlackClient(
        bot_token=settings.SLACK_BOT_TOKEN,
        user_token=settings.SLACK_USER_TOKEN,
        admin_token=settings.SLACK_ADMIN_TOKEN,
    )


@router.get(
    "/auth",
    summary="Slack authentication status",
    description="Returns non-sensitive authentication details from the configured Slack token.",
)
async def auth() -> dict[str, Any]:
    client = _build_client()
    auth_payload = client.auth_test()
    return {
        "ok": auth_payload.get("ok"),
        "team_id": auth_payload.get("team_id"),
        "team": auth_payload.get("team"),
        "user_id": auth_payload.get("user_id"),
        "user": auth_payload.get("user"),
    }


@router.get(
    "/workspace",
    summary="Slack workspace metadata",
    description="Returns normalized workspace metadata available from Slack for the active token.",
)
async def workspace() -> dict[str, Any]:
    client = _build_client()
    return get_workspace_info(client)


@router.get(
    "/users",
    summary="Slack users",
    description="Returns the normalized list of Slack workspace users, including available identity metadata when returned by Slack.",
)
async def users() -> dict[str, Any]:
    client = _build_client()
    return list_slack_users(client)


@router.get(
    "/users/mapping",
    summary="Slack user to employee mapping",
    description="Returns a mapping model for future employee identity synchronization, without inventing any central employee identifiers.",
)
async def users_mapping() -> dict[str, Any]:
    client = _build_client()
    return get_user_mapping(client)


@router.get(
    "/license",
    summary="Slack license information",
    description="Attempts to retrieve Slack commercial license and billing information when the token and scopes support it. Otherwise returns a permission-aware not-available response.",
)
async def slack_license() -> dict[str, Any]:
    client = _build_client()
    payload = get_license_data(client)
    if not payload.get("license_data_available", False):
        return {
            "application": "Slack",
            "license_data_available": False,
            "reason": "Slack billing/license information requires additional administrative permissions or an Enterprise/admin API.",
            "required_action": "Configure the appropriate Slack admin/user token and scopes.",
        }
    return payload


@router.get(
    "/usage",
    summary="Slack usage information",
    description="Returns real usage data from Slack when available, while clearly separating user status, assignment, and active usage data.",
)
async def usage() -> dict[str, Any]:
    client = _build_client()
    return get_usage_summary(client)


@router.get(
    "/inventory",
    summary="Combined Slack inventory",
    description="Combines normalized workspace, user, license, and usage information into a central inventory payload ready for future database synchronization.",
)
async def inventory() -> dict[str, Any]:
    client = _build_client()
    workspace_info = get_workspace_info(client)
    users_payload = list_slack_users(client)
    license_payload = get_license_data(client)
    usage_payload = get_usage_summary(client)
    return build_inventory_payload(
        workspace_info,
        license_payload,
        users_payload,
        usage_payload,
    )


@router.get(
    "/optimization",
    summary="Slack optimization recommendations",
    description="Returns recommendation objects for inventory optimization without making any automatic license changes or removals.",
)
async def optimization() -> dict[str, Any]:
    client = _build_client()
    users_payload = list_slack_users(client)
    usage_payload = get_usage_summary(client)
    license_payload = get_license_data(client)
    return get_optimization_recommendations(
        users_payload,
        usage_payload,
        license_payload,
    )