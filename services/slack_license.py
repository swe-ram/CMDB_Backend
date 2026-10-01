from typing import Any

from services.slack_client import SlackClient


def get_license_data(client: SlackClient) -> dict[str, Any]:
    base_response: dict[str, Any] = {
        "application": "Slack",
        "plan": None,
        "license_type": None,
        "entitled_quantity": None,
        "assigned_quantity": None,
        "available_quantity": None,
        "renewal_date": None,
        "cost": None,
        "currency": None,
        "data_source": "Slack API",
        "data_available": False,
        "reason": None,
        "required_action": None,
    }

    token = client.get_token_for_scope("billing")
    if not token:
        return {
            **base_response,
            "reason": "Slack billing/license information requires additional administrative permissions or an Enterprise/admin API.",
            "required_action": "Configure the appropriate Slack admin/user token and scopes.",
            "license_data_available": False,
        }

    try:
        team_info = client.request("team.info", token=token)
        team_data = team_info.get("team", {}) if isinstance(team_info, dict) else {}
        plan_name = team_data.get("plan", {}).get("name") if isinstance(team_data.get("plan"), dict) else None
        if plan_name:
            base_response["plan"] = plan_name
    except Exception:
        pass

    try:
        billable_info = client.request("team.billableInfo", params={"limit": 200}, token=token)
        billable_data = billable_info.get("billable_info", {}) if isinstance(billable_info, dict) else {}
        if isinstance(billable_data, dict):
            base_response["assigned_quantity"] = len(billable_data)
            base_response["license_type"] = "billable_users"
            base_response["data_available"] = True
    except Exception:
        pass

    if base_response["data_available"]:
        entitled = base_response.get("entitled_quantity")
        assigned = base_response.get("assigned_quantity")
        if entitled is not None and assigned is not None:
            base_response["available_quantity"] = max(entitled - assigned, 0)

    return {
        **base_response,
        "license_data_available": base_response["data_available"],
    }


def get_slack_license_info() -> dict[str, Any]:
    client = SlackClient(
        bot_token=None,
        user_token=None,
        admin_token=None,
    )
    return get_license_data(client)