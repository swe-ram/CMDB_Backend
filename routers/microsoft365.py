from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.microsoft365.microsoft365_client import MicrosoftGraphClient, MicrosoftGraphError
from services.microsoft365.microsoft365_license import get_microsoft365_license_inventory
from services.microsoft365.microsoft365_sync import sync_microsoft365_inventory
from services.microsoft365.microsoft365_users import get_microsoft365_user_inventory

router = APIRouter(
    prefix="/microsoft365",
    tags=["Microsoft 365"],
)


def _error_response(exc: MicrosoftGraphError) -> JSONResponse:
    status_code = exc.status_code or 500
    return JSONResponse(
        status_code=status_code,
        content={
            "application": "Microsoft 365",
            "vendor": "Microsoft",
            "authenticated": False,
            "error": exc.message,
        },
    )


@router.get(
    "/auth",
    summary="Microsoft 365 authentication status",
)
async def auth() -> dict[str, Any]:
    try:
        client = MicrosoftGraphClient()
        client.authenticate()
        return {
            "application": "Microsoft 365",
            "authenticated": True,
            "tenant_id": client.tenant_id,
            "message": "Microsoft Graph authentication successful",
        }
    except MicrosoftGraphError as exc:
        return _error_response(exc)


@router.get(
    "/license",
    summary="Microsoft 365 commercial license inventory",
)
async def license() -> dict[str, Any]:
    try:
        return get_microsoft365_license_inventory()
    except MicrosoftGraphError as exc:
        return JSONResponse(
            status_code=exc.status_code or 500,
            content={
                "application": "Microsoft 365",
                "vendor": "Microsoft",
                "data_available": False,
                "total_skus": 0,
                "licenses": [],
                "error": exc.message,
            },
        )


@router.get(
    "/users",
    summary="Microsoft 365 user inventory",
)
async def users() -> dict[str, Any]:
    try:
        return get_microsoft365_user_inventory()
    except MicrosoftGraphError as exc:
        return JSONResponse(
            status_code=exc.status_code or 500,
            content={
                "application": "Microsoft 365",
                "vendor": "Microsoft",
                "data_available": False,
                "total_users": 0,
                "users": [],
                "error": exc.message,
            },
        )


@router.get(
    "/inventory",
    summary="Combined Microsoft 365 inventory",
)
async def inventory() -> dict[str, Any]:
    try:
        license_payload = get_microsoft365_license_inventory()
        users_payload = get_microsoft365_user_inventory()
        licenses = license_payload.get("licenses", [])
        users = users_payload.get("users", [])

        summary = {
            "total_skus": license_payload.get("total_skus", 0),
            "total_purchased": sum(
                int(item.get("purchased_quantity") or 0) for item in licenses
            ),
            "total_assigned": sum(
                int(item.get("assigned_quantity") or 0) for item in licenses
            ),
            "total_available": sum(
                int(item.get("available_quantity") or 0) for item in licenses
            ),
        }

        return {
            "application": "Microsoft 365",
            "vendor": "Microsoft",
            "licenses": licenses,
            "users": users,
            "summary": summary,
            "data_source": "Microsoft Graph API",
        }
    except MicrosoftGraphError as exc:
        return JSONResponse(
            status_code=exc.status_code or 500,
            content={
                "application": "Microsoft 365",
                "vendor": "Microsoft",
                "licenses": [],
                "users": [],
                "summary": {
                    "total_skus": 0,
                    "total_purchased": 0,
                    "total_assigned": 0,
                    "total_available": 0,
                },
                "error": exc.message,
            },
        )


@router.post(
    "/sync",
    summary="Sync Microsoft 365 inventory data into the database",
)
async def sync() -> dict[str, Any]:
    try:
        return sync_microsoft365_inventory()
    except MicrosoftGraphError as exc:
        return JSONResponse(
            status_code=exc.status_code or 500,
            content={
                "success": False,
                "application": "Microsoft 365",
                "licenses_processed": 0,
                "users_processed": 0,
                "assignments_processed": 0,
                "sync_status": "failed",
                "error": exc.message,
            },
        )
    except Exception as exc:  # pragma: no cover - safety guard around DB sync failures
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "application": "Microsoft 365",
                "licenses_processed": 0,
                "users_processed": 0,
                "assignments_processed": 0,
                "sync_status": "failed",
                "error": str(exc),
            },
        )


@router.get(
    "/sync",
    summary="Legacy GET alias for Microsoft 365 sync",
)
async def sync_get() -> dict[str, Any]:
    return await sync()
