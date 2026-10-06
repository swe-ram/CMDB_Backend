from __future__ import annotations

from datetime import datetime
from typing import Any

from database.database import SessionLocal
from database.microsoft365_repository import (
    save_microsoft365_application,
    save_microsoft365_licenses,
    save_microsoft365_license_assignments,
    save_microsoft365_sync_log,
    save_microsoft365_users,
)
from database.models import License, LicenseAssignment, User


def sync_microsoft365_inventory() -> dict[str, Any]:
    application = save_microsoft365_application()

    try:
        from services.microsoft365.microsoft365_license import get_microsoft365_license_inventory
        from services.microsoft365.microsoft365_users import get_microsoft365_user_inventory

        license_payload = get_microsoft365_license_inventory()
        user_payload = get_microsoft365_user_inventory()

        license_result = save_microsoft365_licenses(
            license_payload.get("licenses", []),
            application=application,
        )
        user_result = save_microsoft365_users(
            user_payload.get("users", []),
            application=application,
        )

        db = SessionLocal()
        try:
            sku_map: dict[str, str] = {}
            for item in license_payload.get("licenses", []):
                sku_id = item.get("sku_id")
                if sku_id:
                    sku_map[sku_id] = (
                        item.get("sku_part_number")
                        or item.get("product")
                        or "Microsoft 365"
                    )

            user_rows = (
                db.query(User)
                .filter(User.application_id == application.id)
                .all()
            )
            user_lookup = {user.external_user_id: user for user in user_rows}

            assignment_records: list[dict[str, Any]] = []
            for user_item in user_payload.get("users", []):
                external_user_id = user_item.get("external_user_id")
                if not external_user_id:
                    continue

                user_row = user_lookup.get(external_user_id)
                if user_row is None:
                    continue

                assigned_skus = user_item.get("assigned_licenses") or []
                seen = set()
                for sku_id in assigned_skus:
                    sku_name = sku_map.get(sku_id)
                    if not sku_name:
                        continue

                    license_row = (
                        db.query(License)
                        .filter(License.application_id == application.id)
                        .filter(
                            (License.product == sku_name)
                            | (License.license_type == sku_name)
                        )
                        .first()
                    )

                    if not license_row or license_row.id in seen:
                        continue

                    seen.add(license_row.id)
                    assignment_records.append(
                        {
                            "license_id": license_row.id,
                            "user_id": user_row.id,
                            "assigned_date": datetime.utcnow(),
                            "status": "assigned",
                        }
                    )

            existing_assignments = (
                db.query(LicenseAssignment)
                .join(License, LicenseAssignment.license_id == License.id)
                .filter(License.application_id == application.id)
                .all()
            )

            current_keys = {
                (record["license_id"], record["user_id"])
                for record in assignment_records
            }

            for assignment in existing_assignments:
                key = (assignment.license_id, assignment.user_id)
                if key not in current_keys:
                    assignment.status = "revoked"
                    assignment.assigned_date = datetime.utcnow()

            db.commit()

            assignment_result = save_microsoft365_license_assignments(
                assignment_records,
                application_id=application.id,
            )

            total_processed = (
                int(license_result.get("total", 0))
                + int(user_result.get("total", 0))
                + int(assignment_result.get("total", 0))
            )

            save_microsoft365_sync_log(
                application_id=application.id,
                status="success",
                records_processed=total_processed,
                error_message=None,
            )

            return {
                "success": True,
                "application": "Microsoft 365",
                "licenses_processed": int(license_result.get("total", 0)),
                "users_processed": int(user_result.get("total", 0)),
                "assignments_processed": int(assignment_result.get("total", 0)),
                "sync_status": "completed",
            }
        finally:
            db.close()
    except Exception as exc:
        try:
            save_microsoft365_sync_log(
                application_id=application.id,
                status="failed",
                records_processed=0,
                error_message=str(exc),
            )
        except Exception:
            pass
        raise
