"""Content-addressed evidence storage."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


class EvidenceRef(BaseModel):
    sha256: str
    path: str
    size: int
    media_type: str
    source: str
    created_at: datetime


class EvidenceStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def add_bytes(self, content: bytes, *, media_type: str, source: str) -> EvidenceRef:
        digest = hashlib.sha256(content).hexdigest()
        directory = self.root / digest[:2] / digest[2:4]
        directory.mkdir(parents=True, exist_ok=True)
        data_path = directory / f"{digest}.bin"
        metadata_path = directory / f"{digest}.json"
        if not data_path.exists():
            data_path.write_bytes(content)
        reference = EvidenceRef(
            sha256=digest,
            path=str(data_path.resolve()),
            size=len(content),
            media_type=media_type,
            source=source,
            created_at=datetime.now(UTC),
        )
        if not metadata_path.exists():
            metadata_path.write_text(
                json.dumps(reference.model_dump(mode="json"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        return reference

    def add_file(self, path: str | Path, *, media_type: str, source: str) -> EvidenceRef:
        return self.add_bytes(Path(path).read_bytes(), media_type=media_type, source=source)
