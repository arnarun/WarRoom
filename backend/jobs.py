"""In-memory registry of scheduler job runs — backs /api/status."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional

from fetchers.common import utcnow


@dataclass
class JobStatus:
    name:          str
    interval_s:    int
    runs:          int = 0
    failures:      int = 0
    running:       bool = False
    last_started:  Optional[str] = None
    last_finished: Optional[str] = None
    last_duration: Optional[float] = None
    last_result:   Optional[int] = None
    last_error:    Optional[str] = None
    last_success:  Optional[str] = None


JOBS: dict[str, JobStatus] = {}


def register(name: str, interval_s: int) -> JobStatus:
    JOBS[name] = JobStatus(name=name, interval_s=interval_s)
    return JOBS[name]


def _iso(dt) -> str:
    return dt.isoformat() + "Z"


def started(name: str):
    j = JOBS[name]
    j.running = True
    j.last_started = _iso(utcnow())
    return utcnow()


def finished(name: str, t0, result=None, error: Exception | None = None):
    j = JOBS[name]
    now = utcnow()
    j.running = False
    j.runs += 1
    j.last_finished = _iso(now)
    j.last_duration = round((now - t0).total_seconds(), 2)
    if error is None:
        j.last_result  = result if isinstance(result, int) else None
        j.last_error   = None
        j.last_success = j.last_finished
    else:
        j.failures  += 1
        # Exception type only — details stay in server logs, /api/status is public
        j.last_error = type(error).__name__


def snapshot() -> list[dict]:
    return [asdict(j) for j in JOBS.values()]
