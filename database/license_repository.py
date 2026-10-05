from datetime import datetime

from sqlalchemy.orm import Session

from database.models import Application, User, License


# =========================================================
# SAVE SLACK USERS
# =========================================================

def save_slack_users(users: list[dict]) -> dict:
    from database.database import SessionLocal

    db: Session = SessionLocal()

    try:

        application = (
            db.query(Application)
            .filter(Application.name == "Slack")
            .first()
        )

        if not application:

            application = Application(
                name="Slack",
                vendor="Slack",
                category="Collaboration",
                status="Active",
                last_sync=datetime.utcnow(),
            )

            db.add(application)
            db.flush()

        else:

            application.last_sync = datetime.utcnow()

        inserted = 0
        updated = 0

        for slack_user in users:

            slack_user_id = slack_user.get(
                "slack_user_id"
            )

            if not slack_user_id:
                continue

            existing_user = (
                db.query(User)
                .filter(
                    User.application_id == application.id,
                    User.external_user_id == slack_user_id,
                )
                .first()
            )

            role = (
                "Owner"
                if slack_user.get("is_owner")
                else "Admin"
                if slack_user.get("is_admin")
                else None
            )

            name = (
                slack_user.get("real_name")
                or slack_user.get("display_name")
                or slack_user.get("name")
            )

            if existing_user:

                existing_user.name = name
                existing_user.email = slack_user.get("email")
                existing_user.status = slack_user.get("status")
                existing_user.role = role

                updated += 1

            else:

                new_user = User(
                    application_id=application.id,
                    external_user_id=slack_user_id,
                    name=name,
                    email=slack_user.get("email"),
                    status=slack_user.get("status"),
                    role=role,
                )

                db.add(new_user)

                inserted += 1

        db.commit()

        return {
            "success": True,
            "application": "Slack",
            "inserted": inserted,
            "updated": updated,
            "total": inserted + updated,
        }

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# =========================================================
# SAVE SLACK LICENSE
# =========================================================

def save_slack_license(
    license_data: dict,
) -> dict:

    from database.database import SessionLocal

    db: Session = SessionLocal()

    try:

        # -------------------------------------------------
        # Get or create Slack application
        # -------------------------------------------------

        application = (
            db.query(Application)
            .filter(Application.name == "Slack")
            .first()
        )

        if not application:

            application = Application(
                name="Slack",
                vendor="Slack",
                category="Collaboration",
                status="Active",
                last_sync=datetime.utcnow(),
            )

            db.add(application)
            db.flush()

        else:

            application.last_sync = datetime.utcnow()

        # -------------------------------------------------
        # License information
        # -------------------------------------------------

        plan = license_data.get("plan")

        product = plan or "Slack"

        license_type = (
            license_data.get("license_type")
            or "billable_users"
        )

        purchased_quantity = (
            license_data.get("purchased_quantity")
        )

        assigned_quantity = (
            license_data.get("assigned_quantity")
        )

        available_quantity = (
            license_data.get("available_quantity")
        )

        used_quantity = (
            license_data.get("active_users")
        )

        cost = license_data.get("cost")
        currency = license_data.get("currency")
        billing_cycle = license_data.get("billing_cycle")
        renewal_date = license_data.get("renewal_date")

        # -------------------------------------------------
        # Check existing license
        # -------------------------------------------------

        existing_license = (
            db.query(License)
            .filter(
                License.application_id == application.id,
                License.license_type == license_type,
            )
            .first()
        )

        if existing_license:

            existing_license.product = product

            existing_license.purchased_qty = (
                purchased_quantity
            )

            existing_license.assigned_qty = (
                assigned_quantity
            )

            existing_license.available_qty = (
                available_quantity
            )

            existing_license.used_qty = (
                used_quantity
            )

            existing_license.cost = cost
            existing_license.currency = currency
            existing_license.billing_cycle = billing_cycle
            existing_license.renewal_date = renewal_date

            existing_license.data_source = (
                license_data.get("data_source")
                or "Slack API"
            )

            existing_license.last_updated = (
                datetime.utcnow()
            )

            action = "updated"
            license_id = existing_license.id

        else:

            new_license = License(

                application_id=application.id,

                product=product,

                license_type=license_type,

                purchased_qty=purchased_quantity,

                assigned_qty=assigned_quantity,

                available_qty=available_quantity,

                used_qty=used_quantity,

                cost=cost,

                currency=currency,

                billing_cycle=billing_cycle,

                renewal_date=renewal_date,

                data_source=(
                    license_data.get("data_source")
                    or "Slack API"
                ),

                last_updated=datetime.utcnow(),
            )

            db.add(new_license)

            db.flush()

            action = "inserted"

            license_id = new_license.id

        db.commit()

        return {
            "success": True,
            "application": "Slack",
            "action": action,
            "license_id": license_id,
            "assigned_quantity": assigned_quantity,
            "active_users": license_data.get(
                "active_users"
            ),
            "inactive_users": license_data.get(
                "inactive_users"
            ),
        }

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()