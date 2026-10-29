"""Read-only real TWL chart measurements; outputs stay in this directory."""
from pathlib import Path
import asyncio
import ctypes
import gc
import json
import sys
import time

import numpy as np
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.api.endpoints import analysis as api


class Counters(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                *[(name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                   "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                   "PagefileUsage", "PeakPagefileUsage")]]


def memory():
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    if not query(handle, ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return {"rss_mib": counters.WorkingSetSize / 1024 ** 2, "peak_rss_mib": counters.PeakWorkingSetSize / 1024 ** 2}


def percentiles(values):
    return {"p50_ms": float(np.percentile(values, 50)), "p95_ms": float(np.percentile(values, 95)),
            "min_ms": min(values), "max_ms": max(values), "n": len(values)}


async def detail(session, state, mode, start, end):
    started = time.perf_counter()
    response = await api.get_chart_data(from_m=float(start), to_m=float(end), max_points=12000,
        file_path=None, line=None, client_session_id=session,
        analysis_revision=state["analysis_revision"], chart_data_mode=mode)
    sampled = time.perf_counter()
    encoded = JSONResponse(response).body
    ended = time.perf_counter()
    resolution = response["chart_resolution"]
    return {"total_ms": (ended - started) * 1000, "route_ms": (sampled - started) * 1000,
            "json_ms": (ended - sampled) * 1000, "bytes": len(encoded),
            "queue_ms": resolution["server_queue_ms"], "sampling_ms": resolution["server_sampling_ms"],
            "source_points": resolution.get("window_source_points", resolution["source_points"]),
            "returned_points": resolution["returned_points"]}


async def measure():
    results = {"scope": "direct FastAPI route plus JSONResponse serialization, no Electron/network/render",
               "raw_cache": "temporary mmap numeric/categorical arrays, 120s idle TTL; no raw DataFrame retained",
               "files": [], "render_ms": None, "heap_mib": None}
    for date in ("20260907", "20260630"):
        path = ROOT / f"00 Reference Document/Raw data/TWL/{date}_TWL_UT.csv"
        before = api._file_digest(path)
        file_result = {"path": str(path), "sha256_before": before, "bytes": path.stat().st_size, "modes": {}}
        for mode in ("median", "raw_overview"):
            session = f"measure-{date}-{mode}"
            request = api.AnalyzeRequest(file_path=str(path), line="TWL", track="UT", section="Mainline",
                session="Mainline", date_str=date, task_no="U1", station_start="CEN", station_end="TSW",
                client_session_id=session, analysis_mode=mode)
            started = time.perf_counter()
            output = api._analyze_sync(request)
            state = api.ANALYSIS_SESSIONS[session]
            domain = output["chart_domain"]
            metric = {"analysis_seconds": time.perf_counter() - started, "domain": domain,
                      "source_points": output["aggregation_metadata"]["source_points"],
                      "representative_points": output["aggregation_metadata"]["representative_points"],
                      "threshold_segments": len(output["threshold_segments"]), "after_analysis_memory": memory()}
            chart_mode = "chainage_median" if mode == "median" else "raw"
            # Release derived arrays to measure a genuine cold index/cache path.
            api._release_chart_cache(state)
            center = (domain["from_m"] + domain["to_m"]) / 2
            metric["cold_detail"] = await detail(session, state, chart_mode, center - 100, center + 100)
            windows = [(float(c - 100), float(c + 100)) for c in np.linspace(domain["from_m"] + 100,
                                                                 domain["to_m"] - 100, 12)]
            samples = [await detail(session, state, chart_mode, *window) for window in windows]
            metric["warm_distinct_windows"] = {name: percentiles([s[name] for s in samples])
                for name in ("total_ms", "json_ms", "queue_ms", "sampling_ms")}
            # Repeated exact viewport demonstrates bounded response-cache reuse.
            cached = [await detail(session, state, chart_mode, *windows[-1]) for _ in range(5)]
            metric["hot_same_window"] = {name: percentiles([s[name] for s in cached])
                for name in ("total_ms", "json_ms", "queue_ms", "sampling_ms")}
            metric["negative_padding"] = await detail(session, state, chart_mode, -919.1600784073908, 16073.0195179871)
            metric["window_cache_entries"] = len(state["chart_windows"].items)
            metric["window_cache_estimated_bytes"] = state["chart_windows"].bytes
            metric["after_detail_memory"] = memory()
            file_result["modes"][mode] = metric
            api._release_chart_cache(state)
            api.ANALYSIS_SESSIONS.pop(session)
            api.LAST_ANALYSIS_SNAPSHOT = None
            api.LAST_ANALYSIS_RESULTS = {}
            del state, output
            gc.collect()
            print(date, mode, "analysis", round(metric["analysis_seconds"], 3),
                  "cold_ms", round(metric["cold_detail"]["total_ms"], 2),
                  "warm_p95_ms", round(metric["warm_distinct_windows"]["total_ms"]["p95_ms"], 2), flush=True)
            file_result["sha256_after"] = api._file_digest(path)
            (Path(__file__).parent / "measurements.partial.json").write_text(json.dumps({**results,
                "current_file": file_result}, indent=2), encoding="utf-8")
        assert file_result["sha256_before"] == file_result["sha256_after"]
        results["files"].append(file_result)
    (Path(__file__).parent / "measurements.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    api.close_chart_caches()
    api.JOBS.close()


if __name__ == "__main__":
    asyncio.run(measure())
