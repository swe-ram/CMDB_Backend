from typing import Any

from services.slack_client import SlackClient


def normalize_slack_user(member: dict[str, Any]) -> dict[str, Any]:
    profile = member.get("profile", {}) or {}
    status = "deleted" if member.get("deleted") else "active"
    if member.get("is_bot"):
        status = "bot"

    return {
        "slack_user_id": member.get("id"),
        "name": member.get("name"),
        "display_name": profile.get("display_name") or member.get("name"),
        "real_name": profile.get("real_name"),
        "email": profile.get("email"),
        "status": status,
        "is_admin": bool(member.get("is_admin")),
        "is_owner": bool(member.get("is_owner")),
        "timezone": member.get("tz"),
    }


def list_slack_users(client: SlackClient) -> dict[str, Any]:
    members = client.paginate("users.list", response_key="members", params={"limit": 200}, token=client.get_token_for_scope("users"))
    normalized = [normalize_slack_user(member) for member in members]
    active_count = sum(1 for item in normalized if item.get("status") == "active")
    deleted_count = sum(1 for item in normalized if item.get("status") == "deleted")

    return {
        "application": "Slack",
        "total_users": len(normalized),
        "active_users": active_count,
        "deleted_users": deleted_count,
        "users": normalized,
    }


def get_user_mapping(client: SlackClient) -> dict[str, Any]:
    users_payload = list_slack_users(client)
    mappings = []
    for user in users_payload.get("users", []):
        mappings.append(
            {
                "slack_user_id": user.get("slack_user_id"),
                "email": user.get("email"),
                "employee_id": None,
                "mapping_status": "pending" if user.get("email") else "missing_email",
            }
        )

    return {
        "application": "Slack",
        "total_mappings": len(mappings),
        "mappings": mappings,
    }
