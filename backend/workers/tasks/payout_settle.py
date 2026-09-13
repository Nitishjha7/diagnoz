from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.dispatch import ServiceDispatch
from app.models.technician import TechnicianProfile
from workers.celery_app import celery_app


@celery_app.task(name="tasks.settle_payouts")
def settle_weekly_payouts():
    """Weekly batch: credit each COMPLETED-but-unsettled dispatch's technician_earnings
    onto that technician's wallet_balance, then stamp it settled_at (dispatch_status
    stays COMPLETED - settlement is a separate concern from the job lifecycle).
    """
    db = SessionLocal()
    settled_count = 0
    total_settled_amount = 0.0

    try:
        unsettled_dispatches = (
            db.query(ServiceDispatch)
            .filter(
                ServiceDispatch.dispatch_status == "COMPLETED",
                ServiceDispatch.settled_at.is_(None),
            )
            .all()
        )

        for dispatch in unsettled_dispatches:
            profile = (
                db.query(TechnicianProfile)
                .filter(TechnicianProfile.user_id == dispatch.technician_id)
                .first()
            )
            if profile is None:
                continue

            earnings = float(dispatch.technician_earnings or 0)
            profile.wallet_balance = float(profile.wallet_balance or 0) + earnings
            dispatch.settled_at = datetime.now(timezone.utc)
            settled_count += 1
            total_settled_amount += earnings

        db.commit()
    finally:
        db.close()

    return {
        "status": "SUCCESS",
        "settled_count": settled_count,
        "total_settled_amount": round(total_settled_amount, 2),
    }
