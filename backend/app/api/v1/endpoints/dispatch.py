from datetime import datetime, timezone

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import generate_otp, hash_otp, verify_otp
from app.models.dispatch import ServiceDispatch
from app.models.technician import TechnicianProfile
from app.models.user import User
from app.schemas.dispatch import DispatchCreate, DispatchCreatedResponse, DispatchOut, OtpVerifyRequest
from app.services.spatial_matcher import (
    acquire_technician_lock,
    find_nearest_available_technician,
    release_technician_lock,
)

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


@router.post("", response_model=DispatchCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_dispatch(
    payload: DispatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("CUSTOMER")),
):
    technician_id = find_nearest_available_technician(db, payload.longitude, payload.latitude)
    if technician_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No available technician found within {settings.DISPATCH_RADIUS_METERS}m",
        )

    if not acquire_technician_lock(technician_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nearest technician is currently being assigned to another job, please retry",
        )

    start_otp = generate_otp()
    end_otp = generate_otp()

    dispatch = ServiceDispatch(
        session_id=payload.session_id,
        customer_id=current_user.id,
        technician_id=technician_id,
        customer_location=from_shape(Point(payload.longitude, payload.latitude), srid=4326),
        dispatch_status="PENDING",
        start_otp_hash=hash_otp(start_otp),
        end_otp_hash=hash_otp(end_otp),
    )
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)

    return DispatchCreatedResponse(dispatch=dispatch, start_otp=start_otp, end_otp=end_otp)


@router.get("/{dispatch_id}", response_model=DispatchOut)
def get_dispatch(
    dispatch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("CUSTOMER", "TECHNICIAN", "ADMIN")),
):
    dispatch = db.get(ServiceDispatch, dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found")
    return dispatch


@router.post("/{dispatch_id}/accept", response_model=DispatchOut)
def accept_dispatch(
    dispatch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("TECHNICIAN")),
):
    dispatch = db.get(ServiceDispatch, dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found")
    if dispatch.technician_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to you")
    if dispatch.dispatch_status != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot accept from status {dispatch.dispatch_status}")

    dispatch.dispatch_status = "ACCEPTED"

    profile = db.query(TechnicianProfile).filter(TechnicianProfile.user_id == current_user.id).first()
    if profile is not None:
        profile.is_available = False

    db.commit()
    db.refresh(dispatch)
    return dispatch


@router.post("/{dispatch_id}/verify-start-otp", response_model=DispatchOut)
def verify_start_otp(
    dispatch_id: str,
    payload: OtpVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("TECHNICIAN")),
):
    dispatch = db.get(ServiceDispatch, dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found")
    if dispatch.technician_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to you")
    if dispatch.dispatch_status != "ACCEPTED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot start from status {dispatch.dispatch_status}")
    if not verify_otp(payload.otp, dispatch.start_otp_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid start OTP")

    dispatch.dispatch_status = "IN_PROGRESS"
    db.commit()
    db.refresh(dispatch)
    return dispatch


@router.post("/{dispatch_id}/verify-end-otp", response_model=DispatchOut)
def verify_end_otp(
    dispatch_id: str,
    payload: OtpVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("TECHNICIAN")),
):
    dispatch = db.get(ServiceDispatch, dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found")
    if dispatch.technician_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to you")
    if dispatch.dispatch_status != "IN_PROGRESS":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot complete from status {dispatch.dispatch_status}")
    if not verify_otp(payload.otp, dispatch.end_otp_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid end OTP")

    fee = float(dispatch.total_service_fee or 0)
    commission = round(fee * settings.PLATFORM_COMMISSION_RATE, 2)
    tds = round((fee - commission) * settings.TDS_RATE, 2)
    dispatch.platform_commission_fee = commission
    dispatch.technician_earnings = round(fee - commission - tds, 2)
    dispatch.dispatch_status = "COMPLETED"
    dispatch.completed_at = datetime.now(timezone.utc)

    profile = db.query(TechnicianProfile).filter(TechnicianProfile.user_id == current_user.id).first()
    if profile is not None:
        profile.is_available = True

    db.commit()
    db.refresh(dispatch)
    release_technician_lock(dispatch.technician_id)
    return dispatch
