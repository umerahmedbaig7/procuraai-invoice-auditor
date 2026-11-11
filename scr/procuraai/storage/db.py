"""SQLite persistence (SQLAlchemy). Stores audit-run metadata, document metadata (never file contents) and findings."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now(timezone.utc)


class DocumentRow(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))        # path only; contents stay on disk, not in the DB
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditRow(Base):
    __tablename__ = "audit_runs"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")        # queued | running | completed | completed_with_errors | failed
    input_mode: Mapped[str] = mapped_column(String(20), default="documents")
    document_ids: Mapped[str] = mapped_column(Text, default="[]")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    findings: Mapped[list["FindingRow"]] = relationship(back_populates="audit", cascade="all, delete-orphan")


class FindingRow(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(String(120), index=True)
    code: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(12))
    payload: Mapped[str] = mapped_column(Text)
    audit: Mapped[AuditRow] = relationship(back_populates="findings")


class Store:
    def __init__(self, url: str = "sqlite:///procuraai.db"):
        self.engine = create_engine(url, future=True, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(self.engine, expire_on_commit=False)

    def add_document(self, doc_id: str, filename: str, path: Path, data: bytes | None = None) -> DocumentRow:
        sha = hashlib.sha256(data).hexdigest() if data is not None else hashlib.sha256(Path(path).read_bytes()).hexdigest()
        row = DocumentRow(id=doc_id, filename=filename, stored_path=str(path), size_bytes=len(data) if data is not None else Path(path).stat().st_size, sha256=sha)
        with self.Session() as s:
            s.add(row); s.commit()
        return row

    def get_documents(self, ids: list[str]) -> list[DocumentRow]:
        with self.Session() as s:
            return list(s.scalars(select(DocumentRow).where(DocumentRow.id.in_(ids))))

    def create_audit(self, audit_id: str, input_mode: str, document_ids: list[str]) -> AuditRow:
        with self.Session() as s:
            row = AuditRow(id=audit_id, input_mode=input_mode, document_ids=json.dumps(document_ids))
            s.add(row); s.commit()
            return row

    def update_status(self, audit_id: str, status: str, error: str | None = None):
        with self.Session() as s:
            row = s.get(AuditRow, audit_id)
            row.status, row.error = status, error
            s.commit()

    def save_report(self, audit_id: str, report: dict, status: str):
        with self.Session() as s:
            row = s.get(AuditRow, audit_id)
            row.status, row.report_json, row.summary_json, row.finished_at = status, json.dumps(report, default=str), json.dumps(report.get("summary", {}), default=str), _now()
            for inv in report.get("invoices", []):
                for f in inv.get("findings", []):
                    s.add(FindingRow(audit_id=audit_id, invoice_id=inv["invoice_id"], code=f["code"], status=f["status"], severity=f["severity"], payload=json.dumps(f, default=str)))
            s.commit()

    def get_audit(self, audit_id: str) -> AuditRow | None:
        with self.Session() as s:
            return s.get(AuditRow, audit_id)

    def findings(self, audit_id: str, severity: str | None = None, status: str | None = None, code: str | None = None, invoice_id: str | None = None) -> list[dict]:
        with self.Session() as s:
            q = select(FindingRow).where(FindingRow.audit_id == audit_id)
            if severity: q = q.where(FindingRow.severity == severity)
            if status: q = q.where(FindingRow.status == status)
            if code: q = q.where(FindingRow.code == code)
            if invoice_id: q = q.where(FindingRow.invoice_id == invoice_id)
            return [json.loads(r.payload) | {"invoice_id": r.invoice_id} for r in s.scalars(q)]

    def counts(self) -> dict:
        with self.Session() as s:
            audits = list(s.scalars(select(AuditRow)))
            return dict(documents=len(list(s.scalars(select(DocumentRow)))), audits=len(audits), audits_by_status={st: sum(1 for a in audits if a.status == st) for st in {a.status for a in audits}},
                        findings=len(list(s.scalars(select(FindingRow)))))
