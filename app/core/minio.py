from minio import Minio

minio_client = Minio(
    "localhost",
    access_key="admin",
    secret_key="admin123456",
    secure=False
)
