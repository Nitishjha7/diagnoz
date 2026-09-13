from fastapi import APIRouter

from app.api.v1.endpoints import auth, dispatch, sessions, streaming, technicians

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sessions.router)
api_router.include_router(streaming.router)
api_router.include_router(technicians.router)
api_router.include_router(dispatch.router)
