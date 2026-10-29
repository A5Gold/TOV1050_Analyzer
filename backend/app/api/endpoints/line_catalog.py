from fastapi import APIRouter

from app.core.line_registry import catalog_payload

router = APIRouter()


@router.get("/line-catalog")
def get_line_catalog():
    """Read-only parent line/branch catalog used by all analysis workflows."""
    return catalog_payload()
