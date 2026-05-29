from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
from io import BytesIO
from pathlib import Path

from .intelligence import extract_from_chunks
from .models import DocumentChunk, IngestionRun, PaperSource, UploadedPaper, new_id, utc_now

logger = logging.getLogger(__name__)


def parse_with_unstructured(content: bytes, filename: str) -> list[tuple[int, str]] | None:
    api_key = os.getenv("UNSTRUCTURED_API_KEY", "")
    if not api_key:
        return None
    try:
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(
            "https://api.unstructured.io/general/v0/general",
            data=body,
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            elements = json.loads(response.read().decode("utf-8"))
        pages: dict[int, list[str]] = {}
        for element in elements:
            text = element.get("text", "").strip()
            metadata = element.get("metadata", {}) or {}
            page_num = metadata.get("page_number", 1)
            if text:
                pages.setdefault(page_num, []).append(text)
        result = [(page, " ".join(texts)) for page, texts in sorted(pages.items())]
        if result:
            logger.info("Unstructured parsed %d pages from %s", len(result), filename)
            return result
    except Exception as exc:
        logger.warning("Unstructured API failed, falling back to local parser: %s", exc)
    return None


def ingest_pdf_bytes(
    project_id: str,
    filename: str,
    content: bytes,
    storage_dir: Path,
    content_type: str = "application/pdf",
) -> UploadedPaper:
    storage_dir.mkdir(parents=True, exist_ok=True)
    paper_id = new_id("paper")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename).strip("_") or f"{paper_id}.pdf"
    path = storage_dir / project_id / f"{paper_id}_{safe_name}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    pages = parse_with_unstructured(content, filename) or extract_pdf_pages(content)
    chunks = [
        DocumentChunk(id=new_id("chunk"), paper_id=paper_id, page_number=page_number, text=text[:4000], created_at=utc_now())
        for page_number, text in pages
        if text.strip()
    ]
    status = "processed" if chunks else "failed"
    message = "Text extracted." if chunks else "No extractable text found."
    run = IngestionRun(
        id=new_id("ingest"),
        paper_id=paper_id,
        status="completed" if chunks else "failed",
        message=message,
        pages_extracted=len(pages),
        chunks_created=len(chunks),
        created_at=utc_now(),
    )
    paper = UploadedPaper(
        id=paper_id,
        project_id=project_id,
        title=Path(filename).stem or "Uploaded paper",
        filename=filename,
        content_type=content_type,
        storage_path=str(path),
        status=status,
        page_count=len(pages),
        chunk_count=len(chunks),
        error="" if chunks else message,
        embedding_status="embedded" if chunks else "failed",
        created_at=utc_now(),
        chunks=chunks,
        ingestion_runs=[run],
    )
    paper.extractions = extract_from_chunks(paper.id, paper.chunks)
    return paper


def extract_pdf_pages(content: bytes) -> list[tuple[int, str]]:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(content))
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((index, clean_text(text)))
        if pages:
            return pages
    except Exception:
        pass

    decoded = content.decode("utf-8", errors="ignore") or content.decode("latin-1", errors="ignore")
    cleaned = clean_text(decoded)
    return [(1, cleaned)] if cleaned else []


def chunks_to_paper_sources(chunks: list[DocumentChunk], max_chunks: int = 8) -> list[PaperSource]:
    sources: list[PaperSource] = []
    for chunk in chunks[:max_chunks]:
        sources.append(
            PaperSource(
                id=f"pdf_{chunk.id}",
                title=f"Uploaded PDF page {chunk.page_number}",
                abstract=chunk.text,
                authors=[],
                year=None,
                url="",
                source="pdf",
                source_type="pdf",
                citation=f"Uploaded PDF chunk {chunk.id}, page {chunk.page_number}.",
                paper_id=chunk.paper_id,
                chunk_id=chunk.id,
                page_number=chunk.page_number,
            )
        )
    return sources


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
