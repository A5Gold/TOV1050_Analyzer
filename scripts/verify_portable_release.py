"""Verify a freshly built portable directory against this checkout and release."""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("portable", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    portable = args.portable.resolve()
    config = portable / "resources/config"
    release = json.loads((ROOT / "config/tov1050-metadata-release.json").read_text(encoding="utf-8"))
    metadata = []
    for entry in release["files"]:
        name = Path(entry["destination"]).name
        packed = config / name
        digest = sha(packed)
        assert digest == entry["approved_sha256"] == sha(ROOT / "config" / name), name
        metadata.append({"file": name, "sha256": digest})
    assert sha(config / "tov1050-metadata-release.json") == sha(ROOT / "config/tov1050-metadata-release.json")
    assert not (config / "backups").exists(), "Local metadata backups must not ship"
    forbidden = [str(p.relative_to(portable)) for p in portable.rglob("*") if p.is_file() and (
        p.name.startswith("~$") or p.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".csv", ".datac"}
        or p.name.endswith((".db-wal", ".db-shm", ".activation.tmp")))]
    assert not forbidden, forbidden
    source_backend = ROOT / "backend/dist/backend_server"
    packed_backend = portable / "resources/backend"
    backend = []
    for source in source_backend.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_backend)
        target = packed_backend / relative
        assert sha(source) == sha(target), str(relative)
        backend.append(str(relative))
    app_source = packed_backend / "_internal/app"
    for source in (ROOT / "backend/app").rglob("*.py"):
        target = app_source / source.relative_to(ROOT / "backend/app")
        assert sha(source) == sha(target), str(source)
    result = {
        "status": "passed", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": json.loads((ROOT / "package.json").read_text())["version"],
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "portable_directory": str(portable), "metadata_release": release["release"],
        "metadata": metadata, "backend_file_count": len(backend),
        "backend_exe_sha256": sha(packed_backend / "backend_server.exe"),
        "app_asar_sha256": sha(portable / "resources/app.asar"),
        "exe_sha256": sha(portable / "TOV1050 Analyzer.exe"),
        "local_databases_or_raw_inputs": forbidden,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (portable / "portable-release.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
