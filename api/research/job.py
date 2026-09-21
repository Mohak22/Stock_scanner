# -*- coding: utf-8 -*-
"""
Created on Mon Sep 21 10:53:57 2026

@author: mohak
"""

"""
Research job lifecycle and in-memory job store.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from threading import Lock
from typing import Any
from uuid import uuid4


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ResearchJob:
    job_id: str

    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    stage: str = "Queued"

    result: dict[str, Any] | None = None
    error: str | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def update(
        self,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        stage: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:

        if status is not None:
            self.status = status

        if progress is not None:
            self.progress = max(
                self.progress,
                min(100, progress),
            )

        if stage is not None:
            self.stage = stage

        if result is not None:
            self.result = result

        if error is not None:
            self.error = error

        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "stage": self.stage,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class JobStore:

    def __init__(self) -> None:
        self._jobs: dict[str, ResearchJob] = {}
        self._lock = Lock()

    def create(self) -> ResearchJob:

        job = ResearchJob(
            job_id=str(uuid4())
        )

        with self._lock:
            self._jobs[job.job_id] = job

        return job

    def get(
        self,
        job_id: str,
    ) -> ResearchJob | None:

        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        stage: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> ResearchJob:

        with self._lock:

            job = self._jobs.get(job_id)

            if job is None:
                raise KeyError(
                    f"Research job not found: {job_id}"
                )

            job.update(
                status=status,
                progress=progress,
                stage=stage,
                result=result,
                error=error,
            )

            return job

    def cleanup(
        self,
        max_age_minutes: int = 60,
    ) -> None:

        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(minutes=max_age_minutes)
        )

        with self._lock:

            expired_jobs = [
                job_id
                for job_id, job in self._jobs.items()
                if (
                    job.status
                    in {
                        JobStatus.COMPLETED,
                        JobStatus.FAILED,
                    }
                    and job.updated_at < cutoff
                )
            ]

            for job_id in expired_jobs:
                del self._jobs[job_id]


job_store = JobStore()