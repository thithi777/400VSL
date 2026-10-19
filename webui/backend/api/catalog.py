"""GET /api/catalog, GET /api/lessons/{label}."""
from fastapi import APIRouter, HTTPException, Request

from ..services.catalog import CatalogError

router = APIRouter(tags=["catalog"])


@router.get("/catalog")
def catalog_summary(request: Request):
    return request.app.state.catalog.summary()


@router.get("/lessons/{label}")
def lesson(label: int, request: Request):
    try:
        return request.app.state.catalog.lesson(label)
    except CatalogError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
