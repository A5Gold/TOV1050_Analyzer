"""Read-only HTTP comparison benchmarks against the isolated Electron backend."""
from pathlib import Path
import time
import json
import hashlib
import requests
import ctypes
from ctypes import wintypes
import subprocess


class MemoryCounters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
        *[(name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
          "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]]


def rss(pid):
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = wintypes.HANDLE
    handle = kernel.OpenProcess(0x0410, False, pid)
    if not handle:
        return 0
    try:
        counters = MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize
        return 0
    finally:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/validation-2026-11-03/history-http"
OUT.mkdir(parents=True, exist_ok=True)
sources = [ROOT / "02 Output Document/TWL" / f"{date}_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx"
           for date in ("20260907", "20260630")]
before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
backend_pid = int(subprocess.check_output(["powershell", "-NoProfile", "-Command",
    "(Get-NetTCPConnection -State Listen -LocalPort 8000 | Select-Object -First 1).OwningProcess"], text=True).strip())
runs = []
for base, label in (("http://127.0.0.1:8000/api", "direct"), ("http://localhost:5193/api", "proxy")):
    diagnostics = requests.get(base + "/diagnostics", timeout=10).json()
    assert Path(diagnostics["database_path"]).resolve().is_relative_to(ROOT / "outputs/validation-2026-11-03")
    session = f"benchmark-{label}"
    started = time.perf_counter()
    with sources[0].open("rb") as first, sources[1].open("rb") as second:
        response = requests.post(base + "/analyze/compare/jobs", params={"client_session_id": session},
            files=[("files", (sources[0].name, first)), ("files", (sources[1].name, second))], timeout=60)
    response.raise_for_status()
    job_id = response.json()["job_id"]
    run = {"entry": label, "job_id": job_id, "submit_seconds": time.perf_counter() - started,
           "source_sha256": before, "status_seconds": [], "rss_peak_bytes": 0}
    print(f"START {label} {job_id}", flush=True)
    while time.perf_counter() - started < 1200:
        tick = time.perf_counter()
        response = requests.get(base + f"/jobs/{job_id}", params={"client_session_id": session}, timeout=10)
        response.raise_for_status()
        state = response.json()
        run["status_seconds"].append(time.perf_counter() - tick)
        run["rss_peak_bytes"] = max(run["rss_peak_bytes"], rss(backend_pid))
        if state["status"] in {"ready", "failed", "cancelled"}:
            break
        time.sleep(.5)
    assert state["status"] == "ready", state
    run["compare_seconds"] = time.perf_counter() - started
    result_response = requests.get(base + f"/jobs/{job_id}/result", params={"client_session_id": session}, timeout=10)
    result_response.raise_for_status()
    result = result_response.json()
    run.update(stats=result["stats"], result_bytes=len(result_response.content), metrics=result.get("metrics"))
    run["status_p95_seconds"] = sorted(run["status_seconds"])[int(len(run["status_seconds"]) * .95)]
    run["chart_runs"] = []
    for temperature in ("cold", "warm"):
        tick = time.perf_counter()
        chart = requests.get(base + f"/analyze/compare/jobs/{job_id}/chart",
            params={"client_session_id": session, "cycle": 0}, timeout=90)
        chart.raise_for_status()
        payload = chart.json()
        assert payload["chart_resolution"]["returned_points"] <= 5000
        run["chart_runs"].append({"temperature": temperature, "seconds": time.perf_counter() - tick,
            "payload_bytes": len(chart.content), "resolution": payload["chart_resolution"]})
    exported = requests.get(base + "/export/compare", params={"job_id": job_id, "client_session_id": session}, timeout=30)
    exported.raise_for_status()
    (OUT / f"{label}-repeated.xlsx").write_bytes(exported.content)
    run["source_unchanged"] = all(hashlib.sha256(path.read_bytes()).hexdigest() == before[str(path)] for path in sources)
    assert run["source_unchanged"]
    runs.append(run)
    (OUT / "validation.json").write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"END {label}: {run['stats']}, {run['compare_seconds']:.1f}s", flush=True)
