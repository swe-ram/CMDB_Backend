from typing import Any

from fastapi import HTTPException, status

from services.slack_client import SlackClient


def get_workspace_info(client: SlackClient) -> dict[str, Any]:
    auth_payload = client.auth_test()
    auth_team_id = auth_payload.get("team_id")
    auth_team_name = auth_payload.get("team")

    try:
        team_info = client.request("team.info", token=client.get_token_for_scope("team"))
    except HTTPException:
        team_info = {}

    team_data = team_info.get("team", {}) if isinstance(team_info, dict) else {}
    workspace_name = team_data.get("name") or auth_team_name or None
    workspace_id = team_data.get("id") or auth_team_id or None

    return {
        "application": "Slack",
        "vendor": "Slack",
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "status": "connected" if workspace_id or workspace_name else "error",
    }
