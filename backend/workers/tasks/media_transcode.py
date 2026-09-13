import subprocess
from pathlib import Path

from workers.celery_app import celery_app
from workers.storage import get_s3_client, upload_directory


@celery_app.task(name="tasks.transcode_to_hls", bind=True, max_retries=3)
def transcode_recording_to_hls(self, session_id: str, raw_video_path: str, output_dir: str):
    raw_path = Path(raw_video_path)
    out_path = Path(output_dir) / session_id
    out_path.mkdir(parents=True, exist_ok=True)
    master_playlist_path = out_path / "master.m3u8"

    # -filter_complex splits the decoded input into 3 independently-scaled video streams
    # (a single -vf per output, repeated, only keeps the LAST one - it does not fan out
    # into multiple renditions the way -c:v:N does for codec options).
    filter_complex = (
        "[0:v]split=3[v1][v2][v3];"
        "[v1]scale=w=1920:h=1080[v1out];"
        "[v2]scale=w=1280:h=720[v2out];"
        "[v3]scale=w=854:h=480[v3out]"
    )
    ffmpeg_command = [
        "ffmpeg", "-y", "-i", str(raw_path),
        "-filter_complex", filter_complex,
        "-map", "[v1out]", "-c:v:0", "libx264", "-b:v:0", "4500k",
        "-maxrate:v:0", "4800k", "-bufsize:v:0", "9000k",
        "-map", "[v2out]", "-c:v:1", "libx264", "-b:v:1", "2500k",
        "-maxrate:v:1", "2700k", "-bufsize:v:1", "5000k",
        "-map", "[v3out]", "-c:v:2", "libx264", "-b:v:2", "1000k",
        "-maxrate:v:2", "1100k", "-bufsize:v:2", "2000k",
        "-map", "0:a", "-map", "0:a", "-map", "0:a", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-f", "hls", "-hls_time", "4", "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(out_path / "segment_%v_%03d.ts"),
        "-master_pl_name", "master.m3u8",
        "-var_stream_map", "v:0,a:0 v:1,a:1 v:2,a:2",
        str(out_path / "stream_%v.m3u8"),
    ]
    try:
        subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        raise self.retry(exc=err, countdown=10)

    s3_client = get_s3_client()
    s3_prefix = f"hls/{session_id}"
    upload_directory(s3_client, out_path, s3_prefix)

    return {
        "status": "SUCCESS",
        "master_playlist": str(master_playlist_path),
        "hls_master_playlist_url": f"{s3_prefix}/master.m3u8",
    }
