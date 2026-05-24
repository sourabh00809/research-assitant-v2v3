from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .config import settings
from .models import ObjectStorageRecord, new_id, utc_now


class ObjectStore:
    def put_bytes(self, project_id: str | None, kind: str, name: str, content: bytes, content_type: str) -> ObjectStorageRecord:
        if settings.storage_backend == "minio":
            try:
                from minio import Minio  # type: ignore

                client = Minio(
                    settings.minio_endpoint,
                    access_key=settings.minio_access_key,
                    secret_key=settings.minio_secret_key,
                    secure=False,
                )
                if not client.bucket_exists(settings.minio_bucket):
                    client.make_bucket(settings.minio_bucket)
                import io

                key = f"{project_id or 'global'}/{kind}/{name}"
                client.put_object(settings.minio_bucket, key, io.BytesIO(content), len(content), content_type=content_type)
                return ObjectStorageRecord(
                    id=new_id("obj"),
                    project_id=project_id,
                    name=name,
                    kind=kind,  # type: ignore[arg-type]
                    backend="s3",
                    uri=f"s3://{settings.minio_bucket}/{key}",
                    content_type=content_type,
                    size_bytes=len(content),
                    created_at=utc_now(),
                )
            except Exception:
                pass
        root = settings.storage_dir / "objects" / (project_id or "global") / kind
        root.mkdir(parents=True, exist_ok=True)
        path = root / Path(name).name
        path.write_bytes(content)
        return ObjectStorageRecord(
            id=new_id("obj"),
            project_id=project_id,
            name=name,
            kind=kind,  # type: ignore[arg-type]
            backend="local",
            uri=str(path),
            content_type=content_type,
            size_bytes=len(content),
            created_at=utc_now(),
        )

    def read_bytes(self, record: ObjectStorageRecord) -> bytes:
        if record.backend == "s3":
            from minio import Minio  # type: ignore

            parsed = urlparse(record.uri)
            bucket = parsed.netloc or settings.minio_bucket
            key = parsed.path.lstrip("/")
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=False,
            )
            response = client.get_object(bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        return Path(record.uri).read_bytes()


def storage_health() -> dict:
    try:
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        return {"backend": settings.storage_backend, "status": "ready", "path": str(settings.storage_dir)}
    except Exception as exc:
        return {"backend": settings.storage_backend, "status": "degraded", "error": str(exc)}
