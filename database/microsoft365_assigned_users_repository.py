from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import Application, License, LicenseAssignedUser


def bulk_upsert_assigned_users(
    application_id: int,
    assigned_users: list[dict[str, Any]],
) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        inserted = 0
        updated = 0

        synced_at = datetime.utcnow()
        for row in assigned_users:
            license_id = row.get("license_id")
            user_id = row.get("user_id")
            if not license_id or not user_id:
                continue

            existing = (
                db.query(LicenseAssignedUser)
                .filter(
                    LicenseAssignedUser.license_id == license_id,
                    LicenseAssignedUser.user_id == user_id,
                )
                .first()
            )

            if existing is not None:
                if existing.status == "revoked":
                    existing.assigned_at = row.get("assigned_at") or synced_at
                existing.sku_id = row.get("sku_id")
                existing.display_name = row.get("display_name")
                existing.email = row.get("email")
                existing.external_user_id = row.get("external_user_id")
                existing.status = row.get("status") or "assigned"
                existing.last_synced_at = synced_at
                updated += 1
            else:
                db.add(
                    LicenseAssignedUser(
                        application_id=application_id,
                        license_id=license_id,
                        user_id=user_id,
                        sku_id=row.get("sku_id"),
                        display_name=row.get("display_name"),
                        email=row.get("email"),
                        external_user_id=row.get("external_user_id"),
                        status=row.get("status") or "assigned",
                        assigned_at=row.get("assigned_at") or synced_at,
                        last_synced_at=synced_at,
                    )
                )
                inserted += 1

        db.commit()
        return {
            "success": True,
            "application_id": application_id,
            "inserted": inserted,
            "updated": updated,
            "total": inserted + updated,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_assigned_users_by_license(license_id: int) -> list[dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(LicenseAssignedUser, License)
            .join(License, LicenseAssignedUser.license_id == License.id)
            .filter(LicenseAssignedUser.license_id == license_id)
            .filter(LicenseAssignedUser.status == "assigned")
            .all()
        )

        result: list[dict[str, Any]] = []
        for assigned_row, license_row in rows:
            result.append(
                {
                    "license_id": assigned_row.license_id,
                    "license_name": license_row.product,
                    "user_id": assigned_row.user_id,
                    "display_name": assigned_row.display_name,
                    "email": assigned_row.email,
                    "external_user_id": assigned_row.external_user_id,
                    "status": assigned_row.status,
                    "sku_id": assigned_row.sku_id,
                }
            )
        return sorted(result, key=lambda row: (row["display_name"] or "").casefold())
    finally:
        db.close()


def get_all_assigned_users_by_license() -> dict[str, list[dict[str, Any]]]:
    db: Session = SessionLocal()
    try:
        application = (
            db.query(Application)
            .filter(Application.name == "Microsoft 365")
            .first()
        )
        if application is None:
            return {"licenses": []}

        license_rows = (
            db.query(License)
            .filter(License.application_id == application.id)
            .order_by(License.license_type, License.id)
            .all()
        )
        assigned_rows = (
            db.query(LicenseAssignedUser)
            .join(License, LicenseAssignedUser.license_id == License.id)
            .filter(
                License.application_id == application.id,
                LicenseAssignedUser.application_id == application.id,
                LicenseAssignedUser.status == "assigned",
            )
            .order_by(LicenseAssignedUser.display_name, LicenseAssignedUser.user_id)
            .all()
        )

        users_by_license: dict[int, list[dict[str, Any]]] = {
            license_row.id: [] for license_row in license_rows
        }
        for assigned_row in assigned_rows:
            users = users_by_license.get(assigned_row.license_id)
            if users is not None:
                users.append(
                    {
                        "user_id": assigned_row.user_id,
                        "display_name": assigned_row.display_name,
                        "email": assigned_row.email,
                        "external_user_id": assigned_row.external_user_id,
                        "status": assigned_row.status,
                    }
                )

        return {
            "licenses": [
                {
                    "license_id": license_row.id,
                    "license_name": license_row.license_type,
                    "assigned_count": len(users_by_license[license_row.id]),
                    "users": users_by_license[license_row.id],
                }
                for license_row in license_rows
            ]
        }
    finally:
        db.close()


def mark_stale_assignments_revoked(
    application_id: int,
    current_keys: set[tuple[int, int]] | None = None,
    license_id: int | None = None,
) -> int:
    db: Session = SessionLocal()
    try:
        query = db.query(LicenseAssignedUser).filter(
            LicenseAssignedUser.application_id == application_id,
            LicenseAssignedUser.status != "revoked",
        )
        if license_id is not None:
            query = query.filter(LicenseAssignedUser.license_id == license_id)

        rows = query.all()
        updated = 0
        for row in rows:
            key = (row.license_id, row.user_id)
            if current_keys is None or key not in current_keys:
                row.status = "revoked"
                row.last_synced_at = datetime.utcnow()
                updated += 1

        db.commit()
        return updated
    finally:
        db.close()
