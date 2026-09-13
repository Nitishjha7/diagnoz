from workers.storage import get_s3_client
from app.core.config import settings

s3 = get_s3_client()
s3.download_file(settings.S3_BUCKET, "reports/dispatch-test-1.pdf", "/tmp/downloaded.pdf")
with open("/tmp/downloaded.pdf", "rb") as f:
    header = f.read(5)
print("HEADER:", header)
import os
print("SIZE:", os.path.getsize("/tmp/downloaded.pdf"))
