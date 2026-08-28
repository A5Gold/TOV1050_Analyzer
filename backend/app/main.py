import os
import shutil
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.api.endpoints import analysis, metadata, sessions, database_records, calculation, wear_records, diagnostics, version_difference

APP_VERSION = "2.0.0"

app = FastAPI(title="TOV Analyzer API", version=APP_VERSION)

# CORS Configuration
# Allow all origins for local desktop app (no security risk for localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for desktop app
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Gzip Compression for large JSON responses (Analysis Data)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include Routers
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(version_difference.router, prefix="/api", tags=["version-difference"])
app.include_router(metadata.router, prefix="/api", tags=["metadata"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(database_records.router, prefix="/api", tags=["database-records"])
app.include_router(calculation.router, prefix="/api", tags=["calculation"])
app.include_router(wear_records.router, prefix="/api", tags=["calculation"])
app.include_router(diagnostics.router, prefix="/api", tags=["diagnostics"])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": APP_VERSION}


# Entry point for PyInstaller bundled executable
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
