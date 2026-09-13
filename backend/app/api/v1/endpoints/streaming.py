import os
from pathlib import Path
from typing import Generator

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/videos", tags=["streaming"])

VIDEO_STORAGE_PATH = Path(settings.REFERENCE_VIDEO_PATH)
CHUNK_SIZE_BYTES = 64 * 1024


def file_byte_range_generator(file_path: Path, start: int, chunk_size: int) -> Generator[bytes, None, None]:
    with open(file_path, "rb") as video_file:
        video_file.seek(start)
        remaining = chunk_size
        while remaining > 0:
            data = video_file.read(min(remaining, CHUNK_SIZE_BYTES))
            if not data:
                break
            remaining -= len(data)
            yield data


@router.get("/stream/{video_id}")
async def stream_reference_video(
    video_id: str,
    range: str | None = Header(None),
    current_user: User = Depends(get_current_user),
):
    file_path = VIDEO_STORAGE_PATH / f"{video_id}.mp4"
    if not file_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video file not found")

    file_size = os.path.getsize(file_path)
    if range is None:
        return StreamingResponse(
            file_byte_range_generator(file_path, 0, file_size),
            media_type="video/mp4",
            headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes"},
        )

    range_value = range.strip().lower().replace("bytes=", "")
    start_s, _, end_s = range_value.partition("-")
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else file_size - 1

    if start >= file_size or end >= file_size:
        raise HTTPException(
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            "Requested Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_length = (end - start) + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_length),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(
        file_byte_range_generator(file_path, start, chunk_length),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )
