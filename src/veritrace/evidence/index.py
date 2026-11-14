import base64
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from ..cases.models import FrozenModel
from ..errors import InputError, IntegrityError
from .models import EvidenceRecord


class SearchFilters(FrozenModel):
    family: str | None = None
    target: str | None = Field(default=None, min_length=1, max_length=1024)
    account: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    time_role: str | None = None

    @field_validator("start", "end")
    @classmethod
    def aware(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Search bounds require an explicit timezone")
        return value

    @model_validator(mode="after")
    def ordered(self):
        if self.start and self.end and self.end < self.start:
            raise ValueError("Search time range is reversed")
        return self


class RecordPage(FrozenModel):
    records: list[EvidenceRecord]
    total: int
    next_cursor: str | None


def utc_text(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


class EvidenceIndex:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.executescript('''
          CREATE TABLE IF NOT EXISTS records(case_id TEXT NOT NULL,record_id TEXT NOT NULL,family TEXT,account TEXT,target TEXT,target_key TEXT,is_url INTEGER,order_key TEXT,record_json TEXT NOT NULL,PRIMARY KEY(case_id,record_id));
          CREATE INDEX IF NOT EXISTS records_order ON records(case_id,order_key,record_id);
          CREATE INDEX IF NOT EXISTS records_family ON records(case_id,family);
          CREATE TABLE IF NOT EXISTS times(case_id TEXT,record_id TEXT,role TEXT,utc TEXT);
          CREATE INDEX IF NOT EXISTS times_case_utc ON times(case_id,utc,record_id);
        ''')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.connection.close()

    def add(self, records):
        with self.connection:
            for record in records:
                value = record.model_dump_json()
                old = self.connection.execute("SELECT record_json FROM records WHERE case_id=? AND record_id=?", (record.case_id, record.record_id)).fetchone()
                if old:
                    if old[0] != value:
                        raise IntegrityError("Record ID collision with different evidence contents")
                    continue
                known = [utc_text(t.normalized_utc) for t in record.times if t.normalized_utc is not None]
                order = min(known) if known else "~unknown"
                target = record.target or ""
                self.connection.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?)", (record.case_id, record.record_id, record.family, record.account, target, target.replace("\\", "/").casefold(), int("://" in target), order, value))
                self.connection.executemany("INSERT INTO times VALUES(?,?,?,?)", [(record.case_id, record.record_id, t.role, utc_text(t.normalized_utc)) for t in record.times if t.normalized_utc is not None])

    def get(self, case_id, record_id):
        row = self.connection.execute("SELECT record_json FROM records WHERE case_id=? AND record_id=?", (case_id, record_id)).fetchone()
        if row is None:
            raise InputError("The record does not exist in this case")
        return EvidenceRecord.model_validate_json(row[0])

    def search(self, case_id, filters: SearchFilters, cursor=None, limit=25):
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 25:
            raise InputError("Search page size must be between 1 and 25")
        fingerprint = hashlib.sha256(json.dumps(filters.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
        clauses, params = ["r.case_id=?"], [case_id]
        for field in ("family", "account"):
            if getattr(filters, field) is not None:
                clauses.append(f"r.{field}=?")
                params.append(getattr(filters, field))
        if filters.target is not None:
            clauses.append("((r.is_url=0 AND instr(r.target_key,?)>0) OR (r.is_url=1 AND instr(r.target,?)>0))")
            params.extend([filters.target.replace("\\", "/").casefold(), filters.target])
        if filters.start or filters.end or filters.time_role:
            terms = ["t.case_id=r.case_id", "t.record_id=r.record_id"]
            for key, op in (("start", ">="), ("end", "<=")):
                value = getattr(filters, key)
                if value:
                    terms.append(f"t.utc {op} ?")
                    params.append(utc_text(value))
            if filters.time_role:
                terms.append("t.role=?")
                params.append(filters.time_role)
            clauses.append("EXISTS(SELECT 1 FROM times t WHERE " + " AND ".join(terms) + ")")
        where = " AND ".join(clauses)
        total = self.connection.execute("SELECT COUNT(*) FROM records r WHERE " + where, params).fetchone()[0]
        if cursor:
            try:
                if len(cursor) > 4096:
                    raise ValueError("Oversized cursor")
                state = json.loads(base64.urlsafe_b64decode(cursor.encode()))
                if state["case_id"] != case_id or state["filter"] != fingerprint or not isinstance(state["order"], str) or not isinstance(state["id"], str):
                    raise ValueError("Cursor is not bound to this case/filter")
            except (ValueError, KeyError, TypeError) as exc:
                raise InputError("Invalid or mismatched continuation cursor") from exc
            where += " AND (r.order_key>? OR (r.order_key=? AND r.record_id>?))"
            params.extend([state["order"], state["order"], state["id"]])
        rows = self.connection.execute("SELECT r.record_json,r.order_key,r.record_id FROM records r WHERE " + where + " ORDER BY r.order_key,r.record_id LIMIT ?", [*params, limit + 1]).fetchall()
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit:
            last = page[-1]
            state = {"case_id": case_id, "filter": fingerprint, "order": last[1], "id": last[2]}
            next_cursor = base64.urlsafe_b64encode(json.dumps(state).encode()).decode()
        return RecordPage(records=[EvidenceRecord.model_validate_json(r[0]) for r in page], total=total, next_cursor=next_cursor)
