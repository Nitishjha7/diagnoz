from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.session import DiagnosticSession
from app.models.user import User
from app.schemas.session import DiagnosticSessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=DiagnosticSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("CUSTOMER")),
):
    session = DiagnosticSession(customer_id=current_user.id, session_status="INITIATED")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=DiagnosticSessionOut)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("CUSTOMER", "TECHNICIAN", "ADMIN")),
):
    session = db.get(DiagnosticSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session
