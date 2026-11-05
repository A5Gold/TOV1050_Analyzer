# Build-process-only fallback for a hanging Windows WMI query in Python 3.12.
import os
import platform

def _build_wmi_unavailable(*args, **kwargs):
    raise OSError("Build-only WMI fallback; use sys.getwindowsversion")

if os.name == "nt":
    platform._wmi_query = _build_wmi_unavailable
