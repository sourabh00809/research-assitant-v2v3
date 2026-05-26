from __future__ import annotations

from pathlib import Path

from supabase import Client, create_client

from .config import settings
from .models import ObjectStorageRecord, new_id, utc_now


class ObjectStore:
    def __init__(self) -> None:
        self._client: Client | None = None

    def _get_client(self) -> Client | None:
        if self._client is not None:
            return self._client
        if settings.supabase_url and settings.supabase_service_role_key:
            self._client = create_client(settings.supabase_url, settings.supabase_service_role_key)
            return self._client
        return None

    def put_bytes(self, project_id: str | None, kind: str, name: str, content: bytes, content_type: str) -> ObjectStorageRecord:
        client = self._get_client()
        if client:
            try:
                bucket = settings.supabase_storage_bucket
                path = f"{project_id or 'global'}/{kind}/{name}"
                client.storage.from_(bucket).upload(path, content, {"content-type": content_type})
                return ObjectStorageRecord(
                    id=new_id("obj"),
                    project_id=project_id,
                    name=name,
                    kind=kind,
                    backend="supabase",
                    uri=f"supabase://{bucket}/{path}",
                    content_type=content_type,
                    size_bytes=len(content),
                    created_at=utc_now(),
                )
            except Exception:
                pass
        root = settings.storage_dir / "objects" / (project_id or "global") / kind
        root.mkdir(parents=True, exist_ok=True)
        file_path = root / Path(name).name
        file_path.write_bytes(content)
        return ObjectStorageRecord(
            id=new_id("obj"),
            project_id=project_id,
            name=name,
            kind=kind,
            backend="local",
            uri=str(file_path),
            content_type=content_type,
            size_bytes=len(content),
            created_at=utc_now(),
        )

    def read_bytes(self, record: ObjectStorageRecord) -> bytes:
        if record.backend == "supabase":
            client = self._get_client()
            if not client:
                raise RuntimeError("Supabase client not configured")
            bucket = settings.supabase_storage_bucket
            key = record.uri.replace(f"supabase://{bucket}/", "")
            response = client.storage.from_(bucket).download(key)
            return response
        return Path(record.uri).read_bytes()


def storage_health() -> dict:
    try:
        client = ObjectStore()._get_client()
        status = "ready" if client else "degraded"
        return {"backend": "supabase" if client else "local", "status": status}
    except Exception as exc:
        return {"backend": "supabase", "status": "degraded", "error": str(exc)}
