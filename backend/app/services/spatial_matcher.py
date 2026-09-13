import uuid

import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings

_redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def find_nearest_available_technician(db: Session, longitude: float, latitude: float) -> uuid.UUID | None:
    """PostGIS KNN match: closest AVAILABLE technician within settings.DISPATCH_RADIUS_METERS.

    Uses the <-> KNN distance operator (GIST-index-assisted, O(log N)) combined with
    ST_DWithin as a hard radius filter (::geography cast for accurate great-circle meters).
    """
    row = db.execute(
        text(
            """
            SELECT user_id
            FROM technician_profiles
            WHERE is_available = TRUE
              AND ST_DWithin(
                    current_location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :radius_m
                  )
            ORDER BY current_location <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            LIMIT 1
            """
        ),
        {"lon": longitude, "lat": latitude, "radius_m": settings.DISPATCH_RADIUS_METERS},
    ).first()
    return row[0] if row else None


def acquire_technician_lock(technician_id: uuid.UUID) -> bool:
    """Redis distributed lock: SET NX EX so two dispatchers can't claim the same technician."""
    key = f"lock:technician:{technician_id}"
    return bool(_redis_client.set(key, "1", nx=True, ex=settings.DISPATCH_LOCK_TTL_SECONDS))


def release_technician_lock(technician_id: uuid.UUID) -> None:
    _redis_client.delete(f"lock:technician:{technician_id}")
