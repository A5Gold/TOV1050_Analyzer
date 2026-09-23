"""Generate the authorized explanatory series without exposing credentials."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import os
import subprocess
import sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
HELPER = Path.home() / ".codex/skills/a6api-imagegen/scripts/generate_image.py"

def generate(prompt):
    output = ROOT / (prompt.stem + ".png")
    if output.exists():
        return {"id": prompt.stem, "status": "existing"}
    env = os.environ.copy()
    env.pop("A6_API_KEY", None)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(HELPER), "--prompt-file", str(prompt),
         "--size", "1920*1080", "--quality", "high", "--timeout", "300",
         "--retries", "2", "--output", str(output)],
        env=env, capture_output=True, text=True, encoding="utf-8",
    )
    return {"id": prompt.stem, "exit_code": result.returncode,
            "summary": result.stdout.strip(), "error": result.stderr.strip()}

if __name__ == "__main__":
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = [pool.submit(generate, p) for p in sorted((ROOT / "prompts").glob("*.txt"))]
        for future in as_completed(pending):
            result = future.result()
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            (ROOT / "generation-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
