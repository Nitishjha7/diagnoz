from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.technician import TechnicianProfile
from app.models.user import User
from app.schemas.technician import TechnicianLocationUpdate, TechnicianProfileOut

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.post("/me/profile", response_model=TechnicianProfileOut, status_code=status.HTTP_201_CREATED)
def create_or_update_profile(
    payload: TechnicianLocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("TECHNICIAN")),
):
    profile = db.query(TechnicianProfile).filter(TechnicianProfile.user_id == current_user.id).first()
    point = from_shape(Point(payload.longitude, payload.latitude), srid=4326)

    if profile is None:
        profile = TechnicianProfile(
            user_id=current_user.id,
            skills=[],
            is_available=True,
            current_location=point,
        )
        db.add(profile)
    else:
        profile.current_location = point

    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/me/location", response_model=TechnicianProfileOut)
def update_location(
    payload: TechnicianLocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("TECHNICIAN")),
):
    profile = db.query(TechnicianProfile).filter(TechnicianProfile.user_id == current_user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Technician profile not found")

    profile.current_location = from_shape(Point(payload.longitude, payload.latitude), srid=4326)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/me/availability", response_model=TechnicianProfileOut)
def set_availability(
    is_available: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("TECHNICIAN")),
):
    profile = db.query(TechnicianProfile).filter(TechnicianProfile.user_id == current_user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Technician profile not found")

    profile.is_available = is_available
    db.commit()
    db.refresh(profile)
    return profile
