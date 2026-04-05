"""
Справочник (типы, валюты; список активов клиенту пустой) и поиск/мета активов.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse

from app.core.dependencies import get_current_user
from app.constants import HTTPStatus
from app.domain.services.reference_service import (
    get_reference_data_cached,
    get_reference_fingerprint_str,
    search_reference_assets,
    get_reference_asset_meta,
)
from app.utils.response import success_response

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/assets/search")
async def reference_assets_search(
    q: str = Query("", max_length=200),
    limit: int = Query(25, ge=1, le=100),
    _user: dict = Depends(get_current_user),
):
    items = await search_reference_assets(q, limit)
    return ORJSONResponse(content=success_response(data={"assets": items}))


@router.get("/assets/{asset_id}")
async def reference_asset_meta_route(
    asset_id: int,
    _user: dict = Depends(get_current_user),
):
    meta = await get_reference_asset_meta(asset_id)
    if not meta:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Актив не найден")
    return ORJSONResponse(content=success_response(data={"asset": meta}))


@router.get("/version")
async def reference_version(_user: dict = Depends(get_current_user)):
    """Лёгкий ответ для проверки клиентского кэша (без тела справочника)."""
    await get_reference_data_cached()
    return ORJSONResponse(
        content=success_response(data={"reference_version": get_reference_fingerprint_str()})
    )


@router.get("/")
async def reference_data(_user: dict = Depends(get_current_user)):
    payload = await get_reference_data_cached()
    fp = get_reference_fingerprint_str()
    return ORJSONResponse(
        content=success_response(
            data={
                "reference": payload,
                "reference_version": fp,
            }
        )
    )
