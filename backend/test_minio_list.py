from workers.storage import get_s3_client
from app.core.config import settings

s3 = get_s3_client()
resp = s3.list_objects_v2(Bucket=settings.S3_BUCKET, Prefix="hls/")
for obj in resp.get("Contents", []):
    print(obj["Key"], obj["Size"])
