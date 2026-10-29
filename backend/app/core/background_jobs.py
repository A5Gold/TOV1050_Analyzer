"""Bounded desktop jobs with cooperative cancellation and leased artifacts."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event, RLock
from typing import Any, Callable
import atexit
import logging
import os
import re
import shutil
import tempfile
import time
import uuid


logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    pass


class JobTimedOut(TimeoutError):
    pass


class JobCapacityError(Exception):
    pass


class JobMissing(Exception):
    pass


class JobExpired(Exception):
    pass


class JobNotReady(Exception):
    pass


@dataclass
class Job:
    job_id: str
    kind: str
    client_session_id: str
    analysis_revision: str | None = None
    status: str = "queued"
    stage: str = "queued"
    processed: int = 0
    total: int | None = None
    unit: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    finished_at: float | None = None
    cancel: Event = field(default_factory=Event)
    result: Any = None
    filename: str | None = None
    path: Path | None = None
    downloads: int = 0
    future: Any = None
    work: dict = field(default_factory=dict)
    committed: bool = False


class JobContext:
    def __init__(self, manager: "JobManager", job: Job):
        self.manager, self.job = manager, job

    def check_cancelled(self):
        if self.job.cancel.is_set():
            raise JobCancelled()
        limit = self.manager.execution_timeout_seconds
        if limit is not None and self.job.started_at is not None:
            if time.monotonic() - self.job.started_at >= limit:
                raise JobTimedOut(f"Job execution exceeded {limit:g} seconds; stopped at a safe checkpoint")

    def cancelled(self):
        return self.job.cancel.is_set()

    def progress(self, stage, processed=0, total=None, unit=None):
        self.check_cancelled()
        with self.manager.lock:
            self.job.stage = stage
            self.job.processed = int(processed or 0)
            self.job.total = int(total) if total is not None else None
            self.job.unit = unit

    def publish(self, callback):
        """Cancellation and successful cache publication have one ordering."""
        with self.manager.lock:
            self.check_cancelled()
            result = callback()
            self.job.committed = True
            return result

    def output_path(self):
        return self.manager.directory / f"{self.job.job_id}.xlsx"


class JobManager:
    def __init__(self, directory=None, ttl_seconds=3600, execution_timeout_seconds=None):
        self.lock = RLock()
        self.jobs: dict[str, Job] = {}
        self.expired: dict[str, tuple[str, float]] = {}
        self.pending_deletions: set[Path] = set()
        self.ttl_seconds = ttl_seconds
        self.execution_timeout_seconds = execution_timeout_seconds
        if execution_timeout_seconds is not None and execution_timeout_seconds <= 0:
            raise ValueError("execution_timeout_seconds must be positive or None")
        self.closed = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tov1050-job")
        self.directory = Path(directory) if directory else self._managed_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        atexit.register(self.close)

    @staticmethod
    def _managed_directory():
        root = Path(tempfile.gettempdir()) / "tov1050-analysis-jobs"
        root.mkdir(exist_ok=True)
        for candidate in root.iterdir():
            match = re.fullmatch(r"process-(\d+)-[0-9a-f]{32}", candidate.name)
            if not match or not candidate.is_dir():
                continue
            pid = int(match.group(1))
            try:
                if os.name == "nt":
                    import ctypes
                    from ctypes import wintypes
                    kernel = ctypes.windll.kernel32
                    kernel.OpenProcess.restype = wintypes.HANDLE
                    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                    handle = kernel.OpenProcess(0x1000, False, pid)
                    if handle:
                        kernel.CloseHandle(handle)
                        continue
                    # Access denied is not evidence that a process has ended.
                    if ctypes.windll.kernel32.GetLastError() != 87:
                        continue
                else:
                    os.kill(pid, 0)
                    continue
            except ProcessLookupError:
                pass
            except PermissionError:
                continue
            shutil.rmtree(candidate, ignore_errors=True)
        return root / f"process-{os.getpid()}-{uuid.uuid4().hex}"

    def submit(self, kind, session_id, factory, revision=None):
        """factory runs only after admission and returns the captured work."""
        with self.lock:
            self.cleanup()
            if self.closed:
                raise JobCapacityError("Job service is shutting down")
            active = sum(j.finished_at is None for j in self.jobs.values())
            if active >= 2:
                raise JobCapacityError("One job is running and one is queued; try again shortly")
            work = factory()
            job = Job(uuid.uuid4().hex, kind, session_id, revision)
            self.jobs[job.job_id] = job
            job.work["call"] = work
            job.future = self.executor.submit(self._run, job)
            return self.describe(job)

    def _run(self, job):
        context = JobContext(self, job)
        try:
            with self.lock:
                context.check_cancelled()
                job.status = "running"
                job.started_at = time.monotonic()
                work = job.work.pop("call")
            result = work(context)
            with self.lock:
                if not job.committed:
                    context.check_cancelled()
                job.result = result
                if job.kind == "analysis":
                    job.analysis_revision = result["analysis_revision"]
                job.status, job.stage = "ready", "ready"
        except JobCancelled:
            with self.lock:
                job.status, job.stage = "cancelled", "cancelled"
        except Exception as exc:
            with self.lock:
                job.status, job.stage = "failed", "failed"
                job.error = str(getattr(exc, "detail", exc))
        finally:
            with self.lock:
                # A locked artifact must never retain an admission slot.
                job.finished_at = time.monotonic()
                if job.status != "ready":
                    job.result = None
                    self._remove_artifact(context.output_path())

    def describe(self, job):
        now = job.finished_at or time.monotonic()
        return {key: getattr(job, key) for key in (
            "job_id", "kind", "client_session_id", "analysis_revision", "status",
            "stage", "processed", "total", "unit", "error",
        )} | {"elapsed_seconds": round(now - job.created_at, 3),
              "stage_percent": round(min(job.processed / job.total, 1) * 100, 1)
              if job.total and job.total > 0 else None}

    def get(self, job_id, session_id):
        with self.lock:
            self.cleanup()
            job = self.jobs.get(job_id)
            if job is None or job.client_session_id != session_id:
                if self.expired.get(job_id, (None,))[0] == session_id:
                    raise JobExpired("Job expired; run analysis or export again")
                raise JobMissing("Job not found")
            return job

    def cancel_job(self, job_id, session_id):
        with self.lock:
            job = self.get(job_id, session_id)
            if job.finished_at is None and not job.committed:
                job.cancel.set()
                if job.future.cancel():
                    job.status = job.stage = "cancelled"
                    job.finished_at = time.monotonic()
                    job.work.clear()
                else:
                    job.status = "cancelling"
            return self.describe(job)

    def acquire_download(self, job_id, session_id):
        with self.lock:
            job = self.get(job_id, session_id)
            if job.kind != "export" or job.status != "ready" or not job.path or not job.path.exists():
                raise JobNotReady("Report is not ready to download")
            job.downloads += 1
            return job

    def release_download(self, job):
        with self.lock:
            job.downloads = max(job.downloads - 1, 0)
            self.cleanup()

    def _remove_artifact(self, path):
        """Keep transient Windows file locks retryable without failing requests."""
        try:
            path.unlink(missing_ok=True)
        except OSError:
            if path not in self.pending_deletions:
                logger.warning("Artifact deletion deferred: %s", path, exc_info=True)
            self.pending_deletions.add(path)
        else:
            self.pending_deletions.discard(path)

    def cleanup(self):
        with self.lock:
            for path in tuple(self.pending_deletions):
                self._remove_artifact(path)
            now = time.monotonic()
            for key, job in list(self.jobs.items()):
                if job.finished_at is not None and not job.downloads and now - job.finished_at >= self.ttl_seconds:
                    if job.path:
                        self._remove_artifact(job.path)
                    self.expired[key] = (job.client_session_id, now)
                    del self.jobs[key]
            # Tombstones are small, but still bounded in time and count.
            self.expired = {k: v for k, v in list(self.expired.items())[-1000:]
                            if now - v[1] < max(self.ttl_seconds, 60)}

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            for job in self.jobs.values():
                if job.finished_at is None:
                    job.cancel.set()
                    if job.future.cancel():
                        job.status = job.stage = "cancelled"
                        job.finished_at = time.monotonic()
                        job.work.clear()
        self.executor.shutdown(wait=True, cancel_futures=True)
        shutil.rmtree(self.directory, ignore_errors=True)
        self.jobs.clear()
        self.pending_deletions.clear()
        atexit.unregister(self.close)
